import os
import cv2
import numpy as np
import time
import threading
import tkinter as tk
from ultralytics import YOLO
from pygrabber.dshow_graph import FilterGraph

from screw_vision.screw_analyzer import ScrewAnalyzer
from screw_vision.arduino_bridge import ArduinoBridge 

# Initialize ScrewAnalyzer
screw_analyzer = ScrewAnalyzer(pixels_per_cm=55.0)

# Get screen resolution using tkinter
root = tk.Tk()
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.destroy()
max_window_width = int(screen_width * 0.8)
max_window_height = int(screen_height * 0.8)

def get_camera_index_by_name(camera_name):
    graph = FilterGraph()
    available_cameras = graph.get_input_devices()
    try:
        return available_cameras.index(camera_name)
    except ValueError:
        print(f"Camera '{camera_name}' not found. Available cameras: {available_cameras}")
        return None

# ==========================================
# --- 1. ARDUINO HARDWARE SETUP ---
# ==========================================
# We now initialize the hardware with a single, clean line of code!
arduino = ArduinoBridge()

# ==========================================
# --- 2. YOLO AI SETUP ---
# ==========================================
file_name = "best.pt"
file_path = f"runs\\detect\\train1\\weights\\{file_name}"

try:
    print("Loading AI Brain...")
    model = YOLO(file_path)
    print("Model loaded successfully!\n")
except Exception as e:
    print(f"Critical Error: {file_name} cannot be accessed. Details: {e}")
    arduino.close()
    exit()

# ==========================================
# --- 3. MAIN MENU ---
# ==========================================
print("====================================")
print("   CONVEYOR VISION SYSTEM MENU")
print("====================================")
print("[1] Static Image Test")
print("[2] Live Camera Feed (Multithreaded Averaging)")
choice = None

# ==========================================
# --- 4. EXECUTE SELECTION ---
# ==========================================
try:
    while choice not in ('1', '2'):
        choice = input("Enter 1 or 2: ").strip()
        
        # ==========================================
        # --- 4A. STATIC IMAGE TEST ---
        # ==========================================
        if choice == '1':
            print("\n--- Image Selection ---")
            print("[1] Clean Screw (screw_X)")
            print("[2] Rusted Screw (rusted_X)")
            print("[3] Brown Screw (brown_X)")
            print("[4] Mixed Screws (mixed_X)")

            options = ["clean", "rusted", "brown", "mixed"]
            
            while True:
                type_choice = input("Select image category (1-4): ").strip()
                if type_choice in ['1', '2', '3', '4']:
                    prefix = options[int(type_choice) - 1]
                    break
                print("Invalid input. Please enter a number from 1 to 4.")
                
            num_choice = input(f"Enter the image number for '{prefix}_X' (e.g., 1, 2, 3): ").strip()
            
            base_name = f"{prefix}_{num_choice}"
            image_path = f"assets\\screw_images\\{base_name}.png"
            
            if not os.path.exists(image_path):
                image_path = f"assets\\screw_images\\{base_name}.jpg"
                
            if not os.path.exists(image_path):
                print(f"\n[!] ERROR: File Not Found!")
                arduino.close()
                exit()

            image = cv2.imread(image_path)
            if image is None:
                print(f"\n[!] ERROR: Could not read image.")
                arduino.close()
                exit()

            print(f"\nScanning {image_path} for screws...")
            results = model(image, conf=0.40) 
            annotated_image = results[0].plot() 

            if len(results[0].boxes) > 0:
                print(f"Found {len(results[0].boxes)} screw(s). Analyzing condition...")
                first_screw = True
                
                for box in results[0].boxes:
                    detected_class_id = int(box.cls[0].item())
                    screw_name = model.names[detected_class_id]
                    bbox = box.xyxy[0].cpu().numpy()
                    
                    is_rusted, rust_ratio = screw_analyzer.detect_rust(image, bbox, rust_threshold=0.15)
                    screw_length_cm = screw_analyzer.measure_length(image, bbox)
                    
                    x1, y1 = int(bbox[0]), int(bbox[1])
                    text_y_position = y1 + 25 
                    
                    if is_rusted:
                        final_command = 0
                        print(f" -> RUSTED {screw_name} detected! (Coverage: {rust_ratio * 100:.1f}%, Length: {screw_length_cm:.2f}cm)")
                        cv2.putText(annotated_image, f"RUST ({rust_ratio*100:.0f}%) | {screw_length_cm:.1f}cm", (x1 + 5, text_y_position), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    else:
                        final_command = detected_class_id
                        print(f" -> CLEAN {screw_name} detected. (Length: {screw_length_cm:.2f}cm)")
                        cv2.putText(annotated_image, f"CLEAN | {screw_length_cm:.1f}cm", (x1 + 5, text_y_position), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                    # Send to Arduino via the Bridge!
                    if first_screw:
                        arduino.send_command(final_command)
                        first_screw = False
            
            print("\nPress ANY KEY in the image window or hit Ctrl+C to close it.")
            window_name = "Conveyor Vision System - Image Test"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, max_window_width, max_window_height)
            cv2.imshow(window_name, annotated_image)
            
            while cv2.waitKey(100) == -1:
                pass 

        # ==========================================
        # --- 4B. LIVE CAMERA FEED (AVERAGING) ---
        # ==========================================
        elif choice == '2':
            desired_camera = "USB2.0 WebCamera"
            cam_index = get_camera_index_by_name(desired_camera)

            if cam_index is not None:
                cap = cv2.VideoCapture(cam_index)
            else:
                print("Camera not found. Defaulting to index 0.")
                cap = cv2.VideoCapture(0)
            
            if not cap.isOpened():
                print("Error: Could not open camera.")
                arduino.close()
                exit()

            shared_frame = None
            shared_results = []
            last_command_time = 0
            cooldown_duration = 3.0 
            is_running = True
            data_lock = threading.Lock()

            # --- THE AI BACKGROUND WORKER ---
            def inference_worker():
                global shared_frame, shared_results, last_command_time, is_running
                
                tracked_screws = {}    
                finalized_screws = {}  

                while is_running:
                    with data_lock:
                        if shared_frame is None:
                            frame_to_process = None
                        else:
                            frame_to_process = shared_frame.copy()

                    if frame_to_process is None:
                        time.sleep(0.01)
                        continue

                    # --- SMALLER ACTIVE ZONE ---
                    frame_h, frame_w = frame_to_process.shape[:2]
                    zone_x1 = int(frame_w * 0.35)
                    zone_x2 = int(frame_w * 0.65)
                    zone_y1 = int(frame_h * 0.10)
                    zone_y2 = int(frame_h * 0.70)

                    results = model.track(frame_to_process, conf=0.40, persist=True, tracker="bytetrack.yaml", verbose=False)
                    
                    new_results = []
                    command_to_send = None
                    current_track_ids = set()
                    
                    if len(results[0].boxes) > 0:
                        for box in results[0].boxes:
                            if box.id is None:
                                bbox = box.xyxy[0].cpu().numpy()
                                x1, y1, x2, y2 = map(int, bbox)
                                new_results.append((x1, y1, x2, y2, "ACQUIRING...", (150, 150, 150)))
                                continue

                            track_id = int(box.id[0].item())
                            current_track_ids.add(track_id)
                            
                            bbox = box.xyxy[0].cpu().numpy()
                            x1, y1, x2, y2 = map(int, bbox)
                            
                            center_x = (x1 + x2) / 2
                            center_y = (y1 + y2) / 2
                            in_zone = (zone_x1 < center_x < zone_x2) and (zone_y1 < center_y < zone_y2)
                            
                            if in_zone:
                                if track_id in finalized_screws:
                                    text, color = finalized_screws[track_id]
                                    new_results.append((x1, y1, x2, y2, text, color))
                                else:
                                    if track_id not in tracked_screws:
                                        tracked_screws[track_id] = {'rust': [], 'len': [], 'cls': []}

                                    is_rusted, rust_ratio = screw_analyzer.detect_rust(frame_to_process, bbox, rust_threshold=0.15)
                                    screw_length_cm = screw_analyzer.measure_length(frame_to_process, bbox)
                                    detected_class_id = int(box.cls[0].item())
                                    
                                    tracked_screws[track_id]['rust'].append(rust_ratio)
                                    tracked_screws[track_id]['len'].append(screw_length_cm)
                                    tracked_screws[track_id]['cls'].append(detected_class_id)
                                    
                                    frames_scanned = len(tracked_screws[track_id]['rust'])
                                    text = f"SCANNING ({frames_scanned})..."
                                    new_results.append((x1, y1, x2, y2, text, (0, 255, 255)))

                            else:
                                if track_id in tracked_screws:
                                    data = tracked_screws.pop(track_id)
                                    
                                    if len(data['rust']) > 0:
                                        avg_rust = sum(data['rust']) / len(data['rust'])
                                        avg_len = sum(data['len']) / len(data['len'])
                                        most_common_cls = max(set(data['cls']), key=data['cls'].count)
                                        screw_name = model.names[most_common_cls]
                                        
                                        if avg_rust >= 0.15:
                                            cmd = 0
                                            text = f"RUST ({avg_rust*100:.0f}%) | {avg_len:.1f}cm"
                                            color = (0, 0, 255)
                                        else:
                                            cmd = most_common_cls
                                            text = f"CLEAN | {avg_len:.1f}cm"
                                            color = (0, 255, 0)
                                            
                                        finalized_screws[track_id] = (text, color)
                                        new_results.append((x1, y1, x2, y2, text, color))
                                        
                                        if (time.time() - last_command_time > cooldown_duration):
                                            command_to_send = cmd
                                            if cmd == 0:
                                                print(f"LIVE FINAL: RUSTED {screw_name} (Avg Rust: {avg_rust*100:.1f}%, Len: {avg_len:.1f}cm)")
                                            else:
                                                print(f"LIVE FINAL: CLEAN {screw_name} (Len: {avg_len:.1f}cm)")

                                elif track_id in finalized_screws:
                                    text, color = finalized_screws[track_id]
                                    new_results.append((x1, y1, x2, y2, text, color))
                                else:
                                    new_results.append((x1, y1, x2, y2, "APPROACHING...", (150, 150, 150)))

                    missing_tracks = list(set(tracked_screws.keys()) - current_track_ids)
                    for m_id in missing_tracks:
                        data = tracked_screws.pop(m_id)
                        if len(data['rust']) > 0:
                            avg_rust = sum(data['rust']) / len(data['rust'])
                            avg_len = sum(data['len']) / len(data['len'])
                            most_common_cls = max(set(data['cls']), key=data['cls'].count)
                            screw_name = model.names[most_common_cls]

                            cmd = 0 if avg_rust >= 0.15 else most_common_cls
                            if (time.time() - last_command_time > cooldown_duration):
                                command_to_send = cmd
                                print(f"LIVE FINAL (Lost Tracker): Computed {screw_name} | Cmd: {cmd}")

                    with data_lock:
                        shared_results = new_results
                        
                    # Fire command to Arduino using the Bridge!
                    if command_to_send is not None:
                        arduino.send_command(command_to_send)
                        with data_lock:
                            last_command_time = time.time()

            worker_thread = threading.Thread(target=inference_worker, daemon=True)
            worker_thread.start()

            # --- THE MAIN UI DISPLAY LOOP ---
            print("\nStarting Live Feed! Press 'q' in the window or Ctrl+C in terminal to quit.")
            window_name = "Conveyor Vision System - Live Feed"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, max_window_width, max_window_height)
            cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1) 
            cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 0)

            while True:
                ret, frame = cap.read()
                if not ret: break
                
                with data_lock:
                    shared_frame = frame.copy()
                    current_results = shared_results.copy()
                    current_cooldown_time = last_command_time

                frame_h, frame_w = frame.shape[:2]
                zone_x1, zone_x2 = int(frame_w * 0.35), int(frame_w * 0.65)
                zone_y1, zone_y2 = int(frame_h * 0.10), int(frame_h * 0.70)
                
                cv2.rectangle(frame, (zone_x1, zone_y1), (zone_x2, zone_y2), (255, 150, 0), 2)
                cv2.putText(frame, "ACTIVE SCAN ZONE", (zone_x1 + 5, zone_y1 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 150, 0), 2)
                    
                for (x1, y1, x2, y2, text, color) in current_results:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, text, (x1 + 5, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                if (time.time() - current_cooldown_time <= cooldown_duration):
                    cv2.putText(frame, "COOLDOWN ACTIVE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

                cv2.imshow(window_name, frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
            is_running = False
            worker_thread.join()
            cap.release()

except KeyboardInterrupt:
    print("\n[!] Ctrl+C Detected! Terminating safely...")

# ==========================================
# --- 5. SHUTDOWN ---
# ==========================================
finally:
    cv2.destroyAllWindows()
    # Close the hardware bridge safely
    arduino.close()