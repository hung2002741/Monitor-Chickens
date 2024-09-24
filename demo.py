import cv2
import torch
import pathlib
import subprocess
import os

# Load YOLOv5 model
temp = pathlib.PosixPath
pathlib.PosixPath = pathlib.WindowsPath

# # Load your YOLOv5 model
model_path = './yolov5/best.pt'
model = torch.hub.load('./yolov5', 'custom', path=model_path, source='local')

# Read video from M3U8 file
cap = cv2.VideoCapture("rtsp://long:Xsw!12345@nongdanonline.ddns.net:554/cam/realmonitor?channel=2&subtype=0")

if not cap.isOpened():
    print("Không thể mở file video M3U8!")
    exit()

# Define the desired width and height for resizing
desired_width = 1500  # Change to your desired width
desired_height = 800  # Change to your desired height

# Initialize VideoWriter with the desired resolution
output_video = cv2.VideoWriter('output_with_detection.mp4', cv2.VideoWriter_fourcc(*'H264'), 10, (desired_width, desired_height))

if not output_video.isOpened():
    print("Không thể khởi tạo VideoWriter!")
    cap.release()
    exit()

# Define the desired thickness for bounding boxes

# Loop through each frame
while True:
    ret, frame = cap.read()
    if not ret:
        print("Không thể đọc frame hoặc video đã hết.")
        break

    # Resize frame to the desired resolution
    frame = cv2.resize(frame, (desired_width, desired_height))

    # Run the object detection model on the frame
    results = model(frame)

    # Count the number of detected boxes
    num_boxes = len(results.xyxy[0])  # Get the number of detected boxes

    # Write the count on the frame
    cv2.putText(frame, f'Number of chickens: {num_boxes}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # Draw bounding boxes on the frame
    for box in results.xyxy[0]:
        x1, y1, x2, y2, conf, cls = box
        if conf > 0.25:  # Confidence threshold
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

    # Write the annotated frame to video
    output_video.write(frame)

    # Show the detected frame
    cv2.imshow('Detected Frame', frame)

    # Press 'q' to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
output_video.release()
cv2.destroyAllWindows()

# Convert the MP4 file with detections to M3U8
input_video = 'output_with_detection.mp4'
output_m3u8 = './yolov5/m3u8/official_test_chicken.m3u8'

command = [
    'ffmpeg',
    '-i', input_video,
    '-c:v', 'copy',
    '-c:a', 'aac',
    '-f', 'hls',
    '-hls_time', '60',
    '-hls_playlist_type', 'event',
    '-hls_list_size', '0',  # Keep all segments
    output_m3u8
]

result = subprocess.run(command, stderr=subprocess.PIPE, text=True)

# Check if the M3U8 file was created successfully
if result.returncode == 0 and os.path.exists(output_m3u8):
    print(f"Chuyển đổi thành công: {output_m3u8}")
else:
    print("Đã có lỗi xảy ra trong quá trình chuyển đổi.")
    print("Chi tiết lỗi:", result.stderr)




