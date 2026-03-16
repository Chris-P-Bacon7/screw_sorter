import cv2
from ultralytics import YOLO

# --- 1. Load the Model ---
file_name = "best.pt"
file_path = f"runs\\detect\\train\\weights\\{file_name}"

try:
    model = YOLO(file_path)
    print(f"Model loaded successfully from {file_path}")
except Exception as e:
    print(f"Critical Error: {file_name} cannot be accessed. Details: {e}")
    exit()

# --- 2. Load Your Test Image ---
# Put the name of your test image here (make sure it's in the same folder as this script)
image_name = "screw_4.png"
image_path = f"assets\\screw_images\\{image_name}" 
image = cv2.imread(image_path)

# Safety check just in case the image name is typed wrong
if image is None:
    print(f"Error: Could not find or open the image '{image_name}'.")
    exit()

print(f"Running detection on {image_path}...")

# --- 3. Run Inference ---
# Note: conf=0.90 is VERY strict. If nothing shows up, lower it to 0.50!
results = model(image, conf=0.90) 

# Draw the bounding boxes and labels onto the image
annotated_image = results[0].plot()

# --- 4. Display the Result ---
cv2.imshow("Screw Detection - Static Image", annotated_image)

print("Detection complete. Press ANY KEY in the image window to close it.")

# 0 means wait infinitely until you press a keyboard key
cv2.waitKey(0) 
cv2.destroyAllWindows()