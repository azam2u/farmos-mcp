
import cv2
import time
import sys

def test_concurrent(fps0=30, w0=640, h0=480):
    print(f"--- Testing Video0: {w0}x{h0} @ {fps0} FPS ---")
    
    # Open Cam 0 (Robot)
    cap0 = cv2.VideoCapture(0)
    if not cap0.isOpened():
        print("FAIL: Could not open video0")
        return False
        
    # Force MJPG on Cam 0
    fourcc_mjpg = cv2.VideoWriter_fourcc(*'MJPG')
    cap0.set(cv2.CAP_PROP_FOURCC, fourcc_mjpg)
    cap0.set(cv2.CAP_PROP_FRAME_WIDTH, w0)
    cap0.set(cv2.CAP_PROP_FRAME_HEIGHT, h0)
    cap0.set(cv2.CAP_PROP_FPS, fps0)
    
    # Read to commit
    ret0, frame0 = cap0.read()
    if not ret0:
        print("FAIL: Could not read frame from video0")
        cap0.release()
        return False
        
    actual_fourcc0 = int(cap0.get(cv2.CAP_PROP_FOURCC))
    fourcc_str0 = "".join([chr((actual_fourcc0 >> 8 * i) & 0xFF) for i in range(4)])
    print(f"SUCCESS: video0 active. Codec: {fourcc_str0}")

    # Open Cam 2 (Logger) - DOES NOT SUPPORT MJPG!
    # Must use YUYV (default). limiting resolution to save bandwidth.
    cap2 = cv2.VideoCapture(2)
    if not cap2.isOpened():
        print("FAIL: Could not open video2")
        return False
        
    # Cam 2 only supports YUYV. Try minimal resolution.
    cap2.set(cv2.CAP_PROP_FRAME_WIDTH, 160)
    cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, 120)
    cap2.set(cv2.CAP_PROP_FPS, 30) # Hardware only supports 30
        
    ret2, frame2 = cap2.read()
    if ret2:
        actual_fourcc2 = int(cap2.get(cv2.CAP_PROP_FOURCC))
        fourcc_str2 = "".join([chr((actual_fourcc2 >> 8 * i) & 0xFF) for i in range(4)])
        w2 = int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
        h2 = int(cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"SUCCESS: Both cameras active! Cam2: {w2}x{h2} {fourcc_str2}")
    else:
        print("FAIL: Opened video2 but could not read frame (Bandwidth limited?)")
        
    cap0.release()
    cap2.release()
    return ret2

if __name__ == "__main__":
    # Test Mixed: Cam0 (MJPG 640x480) + Cam2 (YUYV 160x120)
    test_concurrent(30, 640, 480)
