import cv2
from ultralytics import YOLO

file_name = "best.pt"
file_path = f"runs\\detect\\train\\weights\\{file_name}"

try:
    model = YOLO(file_path)
except FileNotFoundError:
    print(f"Critical Error: {file_name} cannot be accessed or does not exist.")
    exit()

cap = cv2.VideoCapture(0)

print("Starting camera...")
print("Press q to quit.")

while cap.isOpened:
    ret, frame = cap.read()

    if ret:
        results = model(frame, conf=0.50)
        annotated_frame = results[0].plot()

        cv2.imshow("Screw Detection", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()