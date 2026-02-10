
import cv2
import time
import os
import argparse
import sys
import requests
from farmOS import farmOS
from urllib.parse import urlparse

def get_farm_client():
    hostname = os.environ.get("FARMOS_HOST", "https://try.farmos.net")
    username = os.environ.get("FARMOS_USER", "mark")
    password = os.environ.get("FARMOS_PASSWORD", "E1D5S9UO5O0S")
    client_id = os.environ.get("FARMOS_CLIENT_ID", "farm")
    client_secret = os.environ.get("FARMOS_CLIENT_SECRET", "")
    
    if not all([hostname, username, password]):
        print("Error: Missing FARMOS environment variables.")
        return None
        
    try:
        # farmOS lib expects hostname without path ?
        parsed = urlparse(hostname)
        base_hostname = f"{parsed.scheme}://{parsed.netloc}"
        
        farm = farmOS(base_hostname, client_id=client_id, client_secret=client_secret)
        token = farm.authorize(username, password)
        return farm
    except Exception as e:
        print(f"Auth Error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log_id", help="FarmOS Log ID to attach images to", required=False)
    parser.add_argument("--duration", type=int, default=30, help="Duration to run in seconds")
    parser.add_argument("--interval", type=int, default=3, help="Interval between captures")
    # Change type to str to support "/dev/video2" path
    parser.add_argument("--camera", type=str, default="2", help="Camera index (2) or path (/dev/video2)")
    parser.add_argument("--start_delay", type=int, default=10, help="Seconds to wait before starting")
    args = parser.parse_args()
    
    # Add startup delay to allow Robot process to claim init sequence
    if args.start_delay > 0:
        print(f"Waiting {args.start_delay} seconds for robot initialization...")
        time.sleep(args.start_delay)
    
    # 1. Init Camera
    # Handle string vs int args for camera
    cam_arg = args.camera
    # Try converting to int if it looks like a number
    if cam_arg.isdigit():
        cam_arg = int(cam_arg)

    print(f"Opening Camera {cam_arg} (FORCE V4L2)...")
    
    # Retry logic
    cap = None
    for i in range(3):
        # Force V4L2 backend to avoid FFMPEG/GStreamer issues with indices
        cap = cv2.VideoCapture(cam_arg, cv2.CAP_V4L2)
        if cap.isOpened():
            break
        print(f"   Retry {i+1}/3 failed...")
        time.sleep(1)

    if not cap or not cap.isOpened():
        print(f"Error: Could not open camera {cam_arg}")
        sys.exit(1)
        
    # Configure for Low Bandwidth (160x120 YUYV) as verified by probe
    # Cam 2 does NOT support MJPG, so we use default (YUYV) but low res.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 160)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 120)
    cap.set(cv2.CAP_PROP_FPS, 15) # Safe low FPS
    
    start_time = time.time()
    
    # 2. Init FarmOS
    farm = get_farm_client()
    if not farm:
        print("Warning: FarmOS connection failed. Saving locally only.")
    
    img_dir = f"images_{int(start_time)}"
    os.makedirs(img_dir, exist_ok=True)
    
    img_count = 0
    host = os.environ.get("FARMOS_HOST", "https://try.farmos.net")
    if host.endswith("/"): host = host[:-1]
    
    try:
        while (time.time() - start_time) < args.duration:
            ret, frame = cap.read()
            if not ret:
                 print("Failed to read frame")
                 time.sleep(1)
                 continue
            
            timestamp = int(time.time())
            filename = os.path.join(img_dir, f"cam_{timestamp}.jpg")
            
            # Save locally
            cv2.imwrite(filename, frame)
            print(f"Captured {filename}")
            
            if farm:
                try:
                    # Upload directly to log's image field if Log ID is present
                    if args.log_id:
                        url = f"{host}/api/log/activity/{args.log_id}/image"
                        with open(filename, 'rb') as f:
                            data = f.read()
                            headers = {
                                "Content-Type": "application/octet-stream",
                                "Content-Disposition": f'file; filename="{os.path.basename(filename)}"'
                            }
                            response = farm.session.post(url, data=data, headers=headers)
                            
                        if response.status_code == 200 or response.status_code == 201: # 201 Created
                             print(f"   Uploaded and linked to Log {args.log_id}")
                        else:
                             print(f"   Upload failed: {response.status_code} {response.text}")
                    else:
                        print("   Skipping upload (No Log ID)")
                        
                except Exception as e:
                    print(f"   Upload Error: {e}")
            
            img_count += 1
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        print(f"Finished. Captured {img_count} images.")

if __name__ == "__main__":
    main()
