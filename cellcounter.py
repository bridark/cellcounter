import sys
import cv2
import numpy as np
import statistics
import tkinter as tk

# Global variables
scale = 1.0
offset_x = 0
offset_y = 0
view_width = 800    # Will be set dynamically
view_height = 600
manual_circles = []
removed_circles = []
param2 = 40
max_radius = 80
hide_circles = False  # <-- NEW: used with 'J' key

# Variables for drag-resizing manual circles
active_manual_circle_index = None
drag_start_y = None
drag_start_radius = None

def get_auto_circles():
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
            x_orig = x / scale
            y_orig = y / scale
            r_orig = r / scale
            auto_list.append((x_orig, y_orig, r_orig))
    return auto_list

def is_circle_removed(circle):
    x, y, r = circle
    for (xr, yr, rr) in removed_circles:
        if np.sqrt((x - xr)**2 + (y - yr)**2) < rr:
            return True
    return False

def count_circular_objects(img_path, param2, max_radius):
    global scale, original_image, manual_circles, removed_circles
    global offset_x, offset_y, view_width, view_height, hide_circles

    height, width = original_image.shape[:2]
    scaled_width = int(width * scale)
    scaled_height = int(height * scale)

    resized = cv2.resize(original_image, (scaled_width, scaled_height))

    # Corrected panning logic: respect zoomed view boundaries
    offset_x = max(0, min(offset_x, scaled_width - view_width))
    offset_y = max(0, min(offset_y, scaled_height - view_height))

    display_image = resized[offset_y:offset_y + view_height, offset_x:offset_x + view_width].copy()

    if hide_circles:
        cv2.imshow("Detected Circles", display_image)
        return

    auto_circles = get_auto_circles()
    combined_circles = [c for c in auto_circles if not is_circle_removed(c)]
    combined_circles.extend(manual_circles)

    areas = []
    for (x, y, r) in combined_circles:
        x_disp = int(x * scale) - offset_x
        y_disp = int(y * scale) - offset_y
        r_disp = int(r * scale)

        if 0 <= x_disp < view_width and 0 <= y_disp < view_height:
            cv2.circle(display_image, (x_disp, y_disp), r_disp, (0, 255, 0), 4)
            cv2.rectangle(display_image, (x_disp - 5, y_disp - 5), (x_disp + 5, y_disp + 5), (0, 128, 255), -1)
            areas.append(np.pi * (r ** 2))

    total_circles = len(combined_circles)
    print(f"Total number of circular objects detected (or added): {total_circles}")

    if len(areas) > 1:
        mean_area = statistics.mean(areas)
        stdev_area = statistics.pstdev(areas)
        rdw = (stdev_area / mean_area) * 100
        print(f"RDW (circle area variation): {rdw:.2f}%")
    elif len(areas) == 1:
        print("Only one visible circle — RDW not applicable.")
    else:
        print("No circles visible in current view — RDW not applicable.")

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
    global scale, manual_circles, removed_circles, param2, max_radius
    global active_manual_circle_index, drag_start_y, drag_start_radius, offset_x, offset_y
    global view_width, view_height

    x_adj = (x + offset_x) / scale
    y_adj = (y + offset_y) / scale

    if event == cv2.EVENT_MOUSEWHEEL:
        center_x = offset_x + view_width // 2
        center_y = offset_y + view_height // 2
        old_scale = scale

        if flags > 0:
            scale += 0.1
        elif flags < 0:
            scale = max(0.1, scale - 0.1)

        scale_change = scale / old_scale
        offset_x = int(center_x * scale_change - view_width // 2)
        offset_y = int(center_y * scale_change - view_height // 2)

        count_circular_objects(image_path, param2, max_radius)

    elif event == cv2.EVENT_LBUTTONDOWN:
        found = False
        for idx, (cx, cy, r) in enumerate(manual_circles):
            if np.sqrt((x_adj - cx) ** 2 + (y_adj - cy) ** 2) <= r:
                active_manual_circle_index = idx
                drag_start_y = y_adj
                drag_start_radius = r
                found = True
                print("Selected manual circle for resizing at:", cx, cy)
                break
        if not found:
            default_radius = 20
            manual_circles.append([x_adj, y_adj, default_radius])
            active_manual_circle_index = len(manual_circles) - 1
            drag_start_y = y_adj
            drag_start_radius = default_radius
            print("Manual circle added at:", x_adj, y_adj)
        count_circular_objects(image_path, param2, max_radius)

    elif event == cv2.EVENT_MOUSEMOVE and (flags & cv2.EVENT_FLAG_LBUTTON):
        if active_manual_circle_index is not None:
            current_y = y_adj
            new_radius = drag_start_radius + (current_y - drag_start_y)
            manual_circles[active_manual_circle_index][2] = max(5, new_radius)
            count_circular_objects(image_path, param2, max_radius)

    elif event == cv2.EVENT_LBUTTONUP:
        active_manual_circle_index = None
        drag_start_y = None
        drag_start_radius = None

    elif event == cv2.EVENT_RBUTTONDOWN:
        removed = False
        auto_circles = get_auto_circles()
        current_circles = [c for c in auto_circles if not is_circle_removed(c)]
        current_circles.extend(manual_circles)
        for circle in current_circles:
            cx, cy, r = circle
            if np.sqrt((x_adj - cx)**2 + (y_adj - cy)**2) <= r:
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
        if len(sys.argv) >= 2:
            image_path = sys.argv[1]
        else:
            image_path = input("Please drag/drop an image here or type/paste the path: ").strip()

        original_image = cv2.imread(image_path)
        if original_image is None:
            print(f"Error: Could not load image at path: {image_path}")
        else:
            # Detect screen size using tkinter
            root = tk.Tk()
            root.withdraw()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            view_width = screen_width
            view_height = screen_height

            # Fullscreen window
            cv2.namedWindow("Detected Circles", cv2.WINDOW_NORMAL)
            cv2.setWindowProperty("Detected Circles", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

            cv2.createTrackbar("Stringency", "Detected Circles", param2, 100, on_stringency_trackbar)
            cv2.createTrackbar("Max Radius", "Detected Circles", max_radius, 200, on_size_trackbar)
            cv2.setMouseCallback("Detected Circles", mouse_callback)

            while True:
                count_circular_objects(image_path, param2, max_radius)
                key = cv2.waitKey(10) & 0xFF

                if key == 27:  # ESC
                    break
                elif key == ord('r'):
                    offset_x = 0
                    offset_y = 0
                elif key == ord('w'):
                    offset_y = max(0, offset_y - 20)  # Move up
                elif key == ord('s'):
                    offset_y = min(int(original_image.shape[0] * scale - view_height), offset_y + 20)  # Move down
                elif key == ord('a'):
                    offset_x = max(0, offset_x - 20)  # Move left
                elif key == ord('d'):
                    offset_x = min(int(original_image.shape[1] * scale - view_width), offset_x + 20)  # Move right
                elif key == ord('j'):
                    hide_circles = True
                else:
                    hide_circles = False

            cv2.destroyAllWindows()

    except Exception as e:
        print("An unexpected error occurred:", str(e))

    input("\nPress Enter to exit...")
