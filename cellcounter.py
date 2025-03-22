import sys
import cv2
import numpy as np

# Global variables
scale = 1.0          # Global zoom level
manual_circles = []  
removed_circles = [] # List of auto-detected circles that the user has removed
param2 = 40          # Initial HoughCircles parameter for detection
max_radius = 80      # Maximum circle radius for HoughCircles

# Variables for drag-resizing manual circles
active_manual_circle_index = None
drag_start_y = None
drag_start_radius = None

def get_auto_circles():
    """
    Run Hough Circle detection on the scaled image and return a list
    of circles in the original image coordinate system.
    Each circle is a tuple (x, y, r).
    """
    global scale, original_image, param2, max_radius
    height, width = original_image.shape[:2]
    scaled_image = cv2.resize(original_image, (int(width * scale), int(height * scale)))
    gray = cv2.cvtColor(scaled_image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    
    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30,
        param1=100, param2=param2, minRadius=10, maxRadius=max_radius
    )
    
    auto_list = []
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        for (x, y, r) in circles:
            # Convert coordinates from scaled image back to original image coordinates
            x_orig = x / scale
            y_orig = y / scale
            r_orig = r / scale
            auto_list.append((x_orig, y_orig, r_orig))
    return auto_list

def is_circle_removed(circle):
    """
    Check if a given circle (in original coordinates) is within any circle 
    that has been flagged as removed.
    """
    x, y, r = circle
    for (xr, yr, rr) in removed_circles:
        if np.sqrt((x - xr)**2 + (y - yr)**2) < rr:
            return True
    return False

def count_circular_objects(img_path, param2, max_radius):
    """
    Run automatic detection, merge with manual additions,
    filter out user-removed circles, and display the result.
    """
    global scale, original_image, manual_circles, removed_circles
    height, width = original_image.shape[:2]
    display_image = cv2.resize(original_image, (int(width * scale), int(height * scale)))
    
    auto_circles = get_auto_circles()
    
    combined_circles = []
    # Include auto-detected circles (if not removed)
    for circle in auto_circles:
        if not is_circle_removed(circle):
            combined_circles.append(circle)
    
    # Include manually added circles
    combined_circles.extend(manual_circles)
    
    # Draw all circles on the display image (convert coordinates by multiplying with scale)
    for (x, y, r) in combined_circles:
        x_disp = int(x * scale)
        y_disp = int(y * scale)
        r_disp = int(r * scale)
        cv2.circle(display_image, (x_disp, y_disp), r_disp, (0, 255, 0), 4)
        cv2.rectangle(display_image, (x_disp - 5, y_disp - 5), (x_disp + 5, y_disp + 5), (0, 128, 255), -1)
    
    total_circles = len(combined_circles)
    print(f"Total number of circular objects detected (or added): {total_circles}")
    cv2.imshow("Detected Circles", display_image)

def on_stringency_trackbar(val):
    global param2
    param2 = val
    count_circular_objects(image_path, param2, max_radius)

def on_size_trackbar(val):
    global max_radius
    max_radius = val
    count_circular_objects(image_path, param2, max_radius)

def mouse_callback(event, x, y, flags, param):
    """
    Extended mouse callback that supports:
    - Zooming via mouse wheel.
    - Left button: new circle creation or selection for resizing.
    - Mouse move: if dragging, adjust the selected manual circle's radius.
    - Left button release: end of resizing.
    - Right button: remove circle.
    """
    global scale, manual_circles, removed_circles, param2, max_radius
    global active_manual_circle_index, drag_start_y, drag_start_radius

    # Handle zoom with the mouse wheel
    if event == cv2.EVENT_MOUSEWHEEL:
        if flags > 0:  # Scroll up -> zoom in
            scale += 0.1
        elif flags < 0:  # Scroll down -> zoom out
            scale = max(0.1, scale - 0.1)
        count_circular_objects(image_path, param2, max_radius)
    
    # Left button down: either select an existing manual circle or add a new one.
    elif event == cv2.EVENT_LBUTTONDOWN:
        x_orig = x / scale
        y_orig = y / scale
        
        # Check if the click is within an existing manual circle.
        found = False
        for idx, (cx, cy, r) in enumerate(manual_circles):
            if np.sqrt((x_orig - cx)**2 + (y_orig - cy)**2) <= r:
                active_manual_circle_index = idx
                drag_start_y = y_orig
                drag_start_radius = r
                found = True
                print("Selected manual circle for resizing at:", cx, cy)
                break
        
        # If not inside any manual circle, add a new one.
        if not found:
            default_radius = 20  # default radius in original coordinates
            manual_circles.append([x_orig, y_orig, default_radius])
            active_manual_circle_index = len(manual_circles) - 1
            drag_start_y = y_orig
            drag_start_radius = default_radius
            print("Manual circle added at:", x_orig, y_orig)
        count_circular_objects(image_path, param2, max_radius)
    
    # Mouse move: if left button is held down, update the radius of the active manual circle.
    elif event == cv2.EVENT_MOUSEMOVE and (flags & cv2.EVENT_FLAG_LBUTTON):
        if active_manual_circle_index is not None:
            current_y = y / scale
            new_radius = drag_start_radius + (current_y - drag_start_y)
            new_radius = max(5, new_radius)
            manual_circles[active_manual_circle_index][2] = new_radius
            count_circular_objects(image_path, param2, max_radius)
    
    # Left button up: end resizing.
    elif event == cv2.EVENT_LBUTTONUP:
        active_manual_circle_index = None
        drag_start_y = None
        drag_start_radius = None
    
    # Right click: remove a circle (manual or auto-detected)
    elif event == cv2.EVENT_RBUTTONDOWN:
        x_orig = x / scale
        y_orig = y / scale
        
        auto_circles = get_auto_circles()
        current_circles = []
        for circle in auto_circles:
            if not is_circle_removed(circle):
                current_circles.append(circle)
        current_circles.extend(manual_circles)
        
        removed = False
        for circle in current_circles:
            cx, cy, r = circle
            if np.sqrt((x_orig - cx)**2 + (y_orig - cy)**2) <= r:
                if circle in manual_circles:
                    manual_circles.remove(circle)
                    print("Manual circle removed at:", cx, cy)
                else:
                    removed_circles.append(circle)
                    print("Auto-detected circle removed at:", cx, cy)
                removed = True
                break
        if not removed:
            print("No circle found at the click position to remove.")
        count_circular_objects(image_path, param2, max_radius)

if __name__ == "__main__":
    try:
        # 1) Get the image path if provided as a command-line argument
        if len(sys.argv) >= 2:
            image_path = sys.argv[1]
        else:
            # 2) If no command-line argument was given, ask in the console
            image_path = input("Please drag/drop an image here or type/paste the path: ").strip()
    
        # Load the original image
        original_image = cv2.imread(image_path)
        if original_image is None:
            print(f"Error: Could not load image at path: {image_path}")
            # Do NOT exit immediately; let user press Enter to close
        else:
            # Create the window and trackbars
            cv2.namedWindow("Detected Circles")
            cv2.createTrackbar("Stringency", "Detected Circles", param2, 100, on_stringency_trackbar)
            cv2.createTrackbar("Max Radius", "Detected Circles", max_radius, 200, on_size_trackbar)
    
            # Set the mouse callback
            cv2.setMouseCallback("Detected Circles", mouse_callback)
    
            # Initial display
            count_circular_objects(image_path, param2, max_radius)
    
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    
    except Exception as e:
        print("An unexpected error occurred:", str(e))
    
    # Finally, pause so the script won't close immediately when double-clicked
    input("\nPress Enter to exit...")
