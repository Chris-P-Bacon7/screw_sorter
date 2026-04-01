import cv2
import numpy as np

def detect_rust(image, bbox, rust_threshold=0.05):
    """
    Analyzes a YOLO bounding box to determine if a screw is rusted.
    
    Args:
        image: The full, original image frame from your camera (in BGR).
        bbox: The YOLO bounding box coordinates [x_min, y_min, x_max, y_max].
        rust_threshold: The percentage of the screw that must be rust to trigger a positive (Default: 10%).
        
    Returns:
        is_rusted (bool): True if rusted, False otherwise.
        rust_ratio (float): The actual percentage of rust detected (for debugging).
    """
    x1, y1, x2, y2 = map(int, bbox)
    h, w = image.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    
    cropped_screw = image[y1:y2, x1:x2]
    
    # Safety check: if the crop is empty or microscopic, abort
    if cropped_screw.size == 0 or cropped_screw.shape[0] < 10 or cropped_screw.shape[1] < 10: 
        return False, 0.0

    # --- THE GRABCUT BACKGROUND REMOVER ---
    # Create empty arrays required by the GrabCut algorithm
    mask = np.zeros(cropped_screw.shape[:2], np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    
    # Define the "Foreground Rectangle". We tell OpenCV that the outer 2 pixels 
    # of the cropped image are definitely the background table/conveyor.
    crop_h, crop_w = cropped_screw.shape[:2]
    rect = (2, 2, crop_w - 4, crop_h - 4)
    
    # Run the algorithm (3 iterations is a perfect balance of speed and accuracy)
    cv2.grabCut(cropped_screw, mask, rect, bgdModel, fgdModel, 3, cv2.GC_INIT_WITH_RECT)
    
    # GrabCut assigns 0 or 2 to background pixels, and 1 or 3 to the screw.
    # We convert this into a pure black and white mask!
    screw_mask = np.where((mask == 2) | (mask == 0), 0, 255).astype('uint8')
    screw_pixels = cv2.countNonZero(screw_mask) 

    # --- EXPANDED RUST COLOR RANGE ---
    hsv_screw = cv2.cvtColor(cropped_screw, cv2.COLOR_BGR2HSV)
    
    lower_rust_1 = np.array([0, 40, 40])
    upper_rust_1 = np.array([25, 255, 255])
    
    lower_rust_2 = np.array([165, 40, 40])
    upper_rust_2 = np.array([180, 255, 255])
    
    mask1 = cv2.inRange(hsv_screw, lower_rust_1, upper_rust_1)
    mask2 = cv2.inRange(hsv_screw, lower_rust_2, upper_rust_2)
    
    # Only look for rust INSIDE the physical GrabCut screw footprint
    rust_mask = cv2.bitwise_and(cv2.bitwise_or(mask1, mask2), screw_mask)
    
    rust_pixels = cv2.countNonZero(rust_mask)
    
    if screw_pixels == 0: return False, 0.0
    
    rust_ratio = rust_pixels / screw_pixels
    
    return (rust_ratio >= rust_threshold), rust_ratio