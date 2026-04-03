import cv2
import numpy as np

class ScrewAnalyzer:
    def __init__(self, pixels_per_cm):
        self.pixels_per_cm = pixels_per_cm
    
    def detect_rust(self, image, bbox, rust_threshold=0.05):
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
        
    # --- RUST VS BROWN SCREW CHECK (UPGRADED) ---
        if rust_ratio >= rust_threshold:
            
            # 1. The "Too Much Rust" Rule 
            # If the screw is 85%+ rust colored, it's almost certainly a solid brown coated deck screw.
            if rust_ratio > 0.85:
                return False, rust_ratio
                
            # 2. The "Patchiness" Test (Contour Analysis)
            # Find all the distinct "islands" or blobs of rust in our mask
            contours, _ = cv2.findContours(rust_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter out microscopic noise (blobs smaller than 5 pixels)
            valid_rust_islands = [cnt for cnt in contours if cv2.contourArea(cnt) > 5]
            island_count = len(valid_rust_islands)
            
            # Find the area of the single largest rust blob
            if island_count > 0:
                largest_island_area = max([cv2.contourArea(cnt) for cnt in valid_rust_islands])
                total_rust_area = cv2.countNonZero(rust_mask)
                
                # Calculate what percentage of the total rust belongs to the single biggest blob
                largest_blob_ratio = largest_island_area / total_rust_area
            else:
                largest_blob_ratio = 0
            
            # --- THE DECISION LOGIC ---
            # A brown screw will have 1 or 2 massive blobs that make up 90%+ of the "rust" mask.
            # A truly rusted screw will have many small islands (speckling).
            
            # If the single biggest blob makes up more than 80% of all detected rust...
            if largest_blob_ratio > 0.80 and island_count < 3:
                # It's a solid continuous coating (Brown Screw)
                return False, rust_ratio
            else:
                # It's patchy and speckled (Rusted Screw)
                return True, rust_ratio
        
        return (rust_ratio >= rust_threshold), rust_ratio
    
    def measure_length(self, image, bbox):
        """
        Analyzes a YOLO bounding box to determine the true length of a screw.
        """
        x1, y1, x2, y2 = map(int, bbox)
        h, w = image.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        cropped_screw = image[y1:y2, x1:x2]
        if cropped_screw.size == 0: 
            return 0.0

        # 1. Create a mask to isolate the physical screw from the background
        # (We use Otsu's method here because it's lightning fast and perfectly fine for geometry)
        gray = cv2.cvtColor(cropped_screw, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, screw_mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 2. Find the shape of the screw
        contours, _ = cv2.findContours(screw_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return 0.0
            
        # Find the single largest object in the crop (which should be the screw)
        largest_contour = max(contours, key=cv2.contourArea)

        # 3. Draw a "Shrink-Wrapped" rotated rectangle around it
        # rect returns: ((center_x, center_y), (width, height), rotation_angle)
        rect = cv2.minAreaRect(largest_contour)
        
        # 4. Find the longest side of that rectangle (that's the screw's length!)
        rect_width, rect_height = rect[1]
        length_in_pixels = max(rect_width, rect_height)

        # 5. Convert to real-world units (if calibrated)
        if self.pixels_per_cm is not None:
            real_length_cm = length_in_pixels / self.pixels_per_cm
            return real_length_cm
        else:
            # If we haven't calibrated it yet, just return the raw pixel count
            return length_in_pixels