import cv2 as cv
import os

# RTSP stream URL
rtsp_url = "rtsp://internsys:Them1kynuanhe@nongdanonlnine.ddns.net:554/cam/realmonitor?channel=2&subtype=0"

# Open the video capture
vcap = cv.VideoCapture(rtsp_url)

if not vcap.isOpened():
    print("Error: Unable to open video stream.")
    exit()

# Directory to save frames
output_dir = 'C:/Users/ADMIN/OneDrive/Desktop/OJT/BBox-Label-Tool/Images'
os.makedirs(output_dir, exist_ok=True)

frame_count = 0

# Desired window size (width x height)
window_width = 800
window_height = 600

while True:
    # Capture frame-by-frame
    ret, frame = vcap.read()
    
    if not ret:
        print("Error: Unable to read frame from stream.")
        break
    
    # Resize the frame to the desired window size
    frame_resized = cv.resize(frame, (window_width, window_height))
    
    # Add instructions to the video frame
    instructions = "Press 'q' to quit, 's' to save"
    cv.putText(frame_resized, instructions, (10, 30), cv.FONT_HERSHEY_SIMPLEX, 
               1, (255, 255, 255), 2, cv.LINE_AA)
    
    # Display the frame with instructions
    cv.imshow('VIDEO', frame_resized)
    
    # Save frame to disk if 's' is pressed
    frame_filename = os.path.join(output_dir, f'frame_{frame_count:04d}.jpg')
    if cv.waitKey(1) & 0xFF == ord('s'):
        cv.imwrite(frame_filename, frame)
        print(f"Saved {frame_filename}")
        frame_count += 1
    
    # Exit when 'q' is pressed
    if cv.waitKey(1) & 0xFF == ord('q'):
        print("Exiting video stream...")
        break

# Release the video capture and close windows
vcap.release()
cv.destroyAllWindows()
