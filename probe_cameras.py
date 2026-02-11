
import cv2
import os

def probe_cameras():
    for i in range(4):
        dev = f"/dev/video{i}"
        if not os.path.exists(dev):
            print(f"{dev}: Not found")
            continue
            
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"{dev}: OK (Captured {frame.shape})")
            else:
                print(f"{dev}: Opened but failed to read")
            cap.release()
        else:
            print(f"{dev}: Failed to open (likely metadata node)")

if __name__ == "__main__":
    probe_cameras()
