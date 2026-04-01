import os
import cv2
import numpy as np
import serial
import time
import tkinter as tk
from ultralytics import YOLO
from vision_controller.rust_detector.rust_detection import detect_rust

# Get screen resolution using tkinter
root = tk.Tk()
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.destroy()
max_window_width = int(screen_width * 0.8)
max_window_height = int(screen_height * 0.8)

# ==========================================
# --- 1. ARDUINO HARDWARE SETUP ---
# ==========================================
ARDUINO_PORT = 'COM7'  # Change this to match your Arduino's COM port!
BAUD_RATE = 9600

try:
    print(f"Connecting to Arduino on {ARDUINO_PORT}...")
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    
    print("Waiting 2 seconds for Arduino to wake up...")
    time.sleep(2) 
    print("Hardware Connection Established!\n")
except Exception as e:
    print(f"\n[!] Hardware Warning: Could not connect to {ARDUINO_PORT}.")
    print("[!] Continuing in 'AI-Only' simulation mode...\n")
    ser = None 

# ==========================================
# --- 2. YOLO AI SETUP ---
# ==========================================
file_name = "best.pt"
file_path = f"runs\\detect\\train2\\weights\\{file_name}"

try:
    print("Loading AI Brain...")
    model = YOLO(file_path)
    print("Model loaded successfully!\n")
except Exception as e:
    print(f"Critical Error: {file_name} cannot be accessed. Details: {e}")
    if ser: ser.close()
    exit()

# ==========================================
# --- 3. MAIN MENU ---
# ==========================================
print("====================================")
print("   CONVEYOR VISION SYSTEM MENU")
print("====================================")
print("[1] Static Image Test")
print("[2] Live Camera Feed (Conveyor Mode)")
choice = None

# ==========================================
# --- 4A. STATIC IMAGE TEST ---
# ==========================================
while choice not in ('1', '2'):
    choice = input("Enter 1 or 2: ").strip()
    if choice == '1':
        print("\n--- Image Selection ---")
        print("[1] Clean Screw (screw_X)")
        print("[2] Rusted Screw (rusted_X)")
        type_choice = input("Select image category (1 or 2): ").strip()
        
        prefix = "screw" if type_choice == '1' else "rusted"
        num_choice = input(f"Enter the image number for '{prefix}_X' (e.g., 1, 2, 3): ").strip()
        
        base_name = f"{prefix}_{num_choice}"
        image_path = f"assets\\screw_images\\{base_name}.png"
        
        if not os.path.exists(image_path):
            image_path = f"assets\\screw_images\\{base_name}.jpg"
            
        if not os.path.exists(image_path):
            print(f"\n[!] ERROR: File Not Found!")
            print(f"    Could not find '{base_name}.png' or '{base_name}.jpg' in the 'assets\\screw_images\\' folder.")
            if ser: ser.close()
            exit()

        image = cv2.imread(image_path)

        if image is None:
            print(f"\n[!] ERROR: The file '{image_path}' exists but OpenCV could not read it.")
            if ser: ser.close()
            exit()

        print(f"\nScanning {image_path} for screws...")
        results = model(image, conf=0.50) 
        annotated_image = results[0].plot() 

        if len(results[0].boxes) > 0:
            print(f"Found {len(results[0].boxes)} screw(s). Analyzing condition...")
            
            # Use a flag so we only send the FIRST screw's command to the Arduino
            first_screw = True
            
            for box in results[0].boxes:
                detected_class_id = int(box.cls[0].item())
                screw_name = model.names[detected_class_id]
                bbox = box.xyxy[0].cpu().numpy()
                
                is_rusted, rust_ratio = detect_rust(image, bbox, rust_threshold=0.15)
                x1, y1 = int(bbox[0]), int(bbox[1])
                text_y_position = y1 + 25 
                
                if is_rusted:
                    final_command = 0
                    print(f" -> RUSTED {screw_name} detected! (Coverage: {rust_ratio * 100:.1f}%) | Command: {final_command}")
                    cv2.putText(annotated_image, f"RUST ({rust_ratio*100:.0f}%)", (x1 + 5, text_y_position), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                else:
                    final_command = detected_class_id
                    print(f" -> CLEAN {screw_name} detected. | Command: {final_command}")
                    cv2.putText(annotated_image, "CLEAN", (x1 + 5, text_y_position), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                # Send hardware command only for the very first screw we analyze
                if first_screw and ser:
                    print(f"--> Firing command '{final_command}' down the USB cable for the first screw...")
                    ser.write(str(final_command).encode('utf-8'))
                    time.sleep(0.5)
                    while ser.in_waiting > 0:
                        print(f"    Arduino Reply: {ser.readline().decode('utf-8').strip()}")
                    first_screw = False
        else:
            print("\nAI scanned the image but did NOT find any screws.")

        print("\nPress ANY KEY in the image window to close it.")
        window_name = "Conveyor Vision System - Image Test"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, max_window_width, max_window_height)
        cv2.imshow(window_name, annotated_image)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 0)
        
        cv2.waitKey(0) 

    # ==========================================
    # --- 4B. LIVE CAMERA FEED ---
    # ==========================================
    elif choice == '2':
        camera_id = 1 
        cap = cv2.VideoCapture(camera_id)
        
        if not cap.isOpened():
            print(f"Error: Could not open camera {camera_id}. Try changing it to 0.")
            if ser: ser.close()
            exit()

        print("\nStarting Live Feed! Press 'q' in the window to quit.")
        
        last_command_time = 0
        cooldown_duration = 3.0 

        while True:
            ret, frame = cap.read()
            if not ret: break
            
            results = model(frame, conf=0.50)
            annotated_frame = results[0].plot()

            if len(results[0].boxes) > 0:
                
                # 1. Visually analyze and draw text for EVERY screw on screen
                for box in results[0].boxes:
                    bbox = box.xyxy[0].cpu().numpy()
                    is_rusted, rust_ratio = detect_rust(frame, bbox, rust_threshold=0.15)
                    x1, y1 = int(bbox[0]), int(bbox[1])
                    text_y_position = y1 + 25
                    
                    if is_rusted:
                        cv2.putText(annotated_frame, f"RUST ({rust_ratio*100:.0f}%)", (x1 + 5, text_y_position), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    else:
                        cv2.putText(annotated_frame, "CLEAN", (x1 + 5, text_y_position), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                # 2. ONLY send a command to the Arduino for the FIRST screw, and only if cooldown is done
                if (time.time() - last_command_time > cooldown_duration):
                    first_box = results[0].boxes[0]
                    detected_class_id = int(first_box.cls[0].item())
                    screw_name = model.names[detected_class_id]
                    bbox = first_box.xyxy[0].cpu().numpy()
                    
                    is_rusted, rust_ratio = detect_rust(frame, bbox, rust_threshold=0.15)
                    
                    if is_rusted:
                        final_command = 0
                        print(f"LIVE: RUSTED {screw_name} seen! Sending command 0.")
                    else:
                        final_command = detected_class_id
                        print(f"LIVE: CLEAN {screw_name} seen! Sending command {final_command}.")

                    if ser:
                        ser.write(str(final_command).encode('utf-8'))
                    
                    last_command_time = time.time()
                
            # Keep displaying the waiting message on screen if the cooldown is active
            if (time.time() - last_command_time <= cooldown_duration):
                cv2.putText(annotated_frame, "COOLDOWN ACTIVE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            window_name = "Conveyor Vision System - Live Feed"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, max_window_width, max_window_height)
            cv2.imshow(window_name, annotated_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        cap.release()

    else:
        print("Invalid choice. Please type 1 or 2.")
        continue
        

# ==========================================
# --- 5. SHUTDOWN ---
# ==========================================
cv2.destroyAllWindows()
if ser:
    ser.close()
    print("\nHardware disconnected safely.")