import cv2
from ultralytics import YOLO

file_name = "best.pt"
file_path = f"runs\\detect\\train2\\weights\\{file_name}"

try:
    model = YOLO(file_path)
except FileNotFoundError:
    print(f"Critical Error: {file_name} cannot be accessed or does not exist.")
    exit()

cap = cv2.VideoCapture(1)

print("Starting camera...")
print("Press q to quit.")

while cap.isOpened:
    ret, frame = cap.read()

    if ret:
        results = model(frame, conf=0.75)
        annotated_frame = results[0].plot()

        cv2.imshow("Screw Detection", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        print("Quitting detection test...")
        break

cap.release()
cv2.destroyAllWindows()