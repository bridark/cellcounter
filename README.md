cellcounter: A quick, simple Python script to detect, add, remove, and resize circles in images using OpenCV. 

Setup
pip install opencv-python numpy 

How to Use
Run from command line: python [script_name].py [image_name].jpg 
Or double-click the script and paste or drag-and-drop your image when asked.

Features & Controls
Auto-detect circles: Adjust detection sensitivity (Stringency) and max size (Max Radius) with sliders. Add circles: Left-click anywhere. Resize circles: Left-click and drag up/down. Remove circles: Right-click circles. Zoom: Scroll wheel to zoom. 
Use WSAD to pan the image. Press and hold J to hide the annotations.

Output
Real-time circle display showing total circle count in console. 

Limitations
This cell counter is not entirely accurate in detecting cells. Other objects that appear circular may also be counted. If a circle is overlapping the edge of an image, it may not be detected.

Notes
Resizing the window may require user to readjust settings to get circles/cells to appear again.
