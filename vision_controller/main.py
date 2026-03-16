import cv2
from ultralytics import YOLO
import serial
import time

# ==========================================
# --- 1. ARDUINO SETUP ---
# ==========================================
ARDUINO_PORT = 'COM7'  # Make sure this is still correct!
BAUD_RATE = 9600

try:
    print(f"Connecting to Arduino on {ARDUINO_PORT}...")
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    
    # Wait for the Arduino to reboot and the IR sensor to stabilize
    print("Waiting 2 seconds for Arduino to wake up...")
    time.sleep(2) 
    print("Connection established!\n")
except Exception as e:
    print(f"Critical Error: Could not connect to {ARDUINO_PORT}. Details: {e}")
    print("Continuing in 'AI-Only' mode (No physical hardware)...\n")
    ser = None

# ==========================================
# --- 2. YOLO AI SETUP ---
# ==========================================
file_name = "best.pt"
file_path = f"runs\\detect\\train\\weights\\{file_name}"

try:
    print("Loading AI Brain...")
    model = YOLO(file_path)
    print("Model loaded successfully!\n")
except Exception as e:
    print(f"Critical Error: {file_name} cannot be accessed. Details: {e}")
    exit()

# ==========================================
# --- 3. RUN THE VISION SYSTEM ---
# ==========================================
# Put the name of your test image here
image_path = "test_screw.jpg" 
image = cv2.imread(image_path)

if image is None:
    print(f"Error: Could not find or open the image '{image_path}'.")
    exit()

print(f"Scanning {image_path} for screws...")

# Run the detection (Adjust conf=0.50 if it misses the screw)
results = model(image, conf=0.50) 
annotated_image = results[0].plot()

# ==========================================
# --- 4. BRIDGE TO PHYSICAL HARDWARE ---
# ==========================================
# Check if the AI actually found any bounding boxes
if len(results[0].boxes) > 0:
    
    # Grab the Class ID (0-4) of the VERY FIRST screw it sees
    # .item() converts the raw tensor math into a standard Python integer
    detected_class_id = int(results[0].boxes.cls[0].item())
    
    # Look up the actual name of the screw based on your YOLO training data
    screw_name = model.names[detected_class_id]
    
    print(f"\nSUCCESS! AI Detected: {screw_name} (Class {detected_class_id})")
    
    # If the Arduino is plugged in, send the command!
    if ser:
        print(f"--> Firing command '{detected_class_id}' down the USB cable...")
        
        # Convert the integer to a string, encode it, and send it
        ser.write(str(detected_class_id).encode('utf-8'))
        
        # Wait half a second for the Arduino to catch it and reply
        time.sleep(0.5)
        
        while ser.in_waiting > 0:
            arduino_reply = ser.readline().decode('utf-8').strip()
            print(f"    Arduino Reply: {arduino_reply}")
else:
    print("\nAI scanned the image but did NOT find any screws.")

# ==========================================
# --- 5. DISPLAY RESULTS ---
# ==========================================
print("\nLook at the machine! Press ANY KEY in the image window to close it.")
cv2.imshow("Conveyor Vision System", annotated_image)
cv2.waitKey(0) 

# Clean up
cv2.destroyAllWindows()
if ser:
    ser.close()