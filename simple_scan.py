
import cv2
print("Probing available cameras...")
for i in range(10):
    cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
    if cap.isOpened():
        print(f"Index {i}: OPEN SUCCESS")
        backend = cap.getBackendName()
        print(f"   Backend: {backend}")
        cap.release()
    else:
        # print(f"Index {i}: FAILED")
        pass
print("Done.")
