import os
import time
import requests
import hmac
import hashlib
import base64
from datetime import datetime, timezone
import email.utils
from watchdog.observers import Observer
from watchdog.events import DirDeletedEvent, FileDeletedEvent, FileSystemEventHandler
from dotenv import load_dotenv
import threading    
import shutil
import numpy as np

# Load environment variables
load_dotenv()

# Get environment variables
HMAC_KEY = os.getenv("HMAC_KEY")
STREAM_FARM_ENDPOINT = os.getenv("STREAM_FARM_ENDPOINT")
STREAM_PEN_ENDPOINT = os.getenv("STREAM_PEN_ENDPOINT")


class VideoUploadHandler(FileSystemEventHandler):
    def __init__(self, repository : str):
        self.repository = repository

    def on_created(self, event):
        print(f"New file detected: {event.src_path}")
        if event.is_directory:
            return None
        # Chỉ tải lên các tệp m3u8 và ts
        if event.src_path.endswith(".ts") or event.src_path.endswith("final_output.m3u8"):
            self.upload_video(event.src_path)


    def upload_video(self, videoFilePath):
        # videoFilePath = videoFilePath.replace("\\", "/")
        print(videoFilePath)
        print(self.repository)

        result = self.repository.split("recorded/")[1]
        folders = result.split('/')
        print(folders)
        if len(folders) == 3:
            penId = folders[-2]
            channelId = folders[-1][-1]
            farmId = folders[-3]
        else:
            farmId = folders[-2]
            channelId = folders[-1][-1]
            penId = None

        # Read the video file as binary
        content = read_file(videoFilePath)

        # Compute the content hash
        contentHash = compute_content_hash(content)

        # Format the current UTC time according to RFC1123
        timestamp_header = get_rfc1123_date()

        # Sign data with the following format
        dataToSign = f'{timestamp_header}\n{contentHash}'

        # Generate the signature
        signature = generate_signature(HMAC_KEY, dataToSign)

        # Create the API URL
        if penId:
            post_url = f"{STREAM_PEN_ENDPOINT}/{farmId}/{penId}/{channelId}"
        else:
            post_url = f"{STREAM_FARM_ENDPOINT}/{farmId}/{channelId}"

        # Headers that need to be sent with the request
        headers = {
            'Authorization': f'Hmac {signature}',
            'x-ms-date': timestamp_header,
            'x-ms-content-sha256': contentHash,
        }

        # Send a POST request to upload the video
        print(f"Uploading video for camera: farmId={farmId}, penId={penId}, channelId={channelId}, videoFile={videoFilePath}")
        print(f"Post URL: {post_url}")
        post_request(post_url, get_file(videoFilePath), headers=headers)

def generate_signature(secret_key, data):
    key = bytes(secret_key, 'utf-8')  # Chuyển đổi secret_key thành bytes
    message = bytes(data, 'utf-8')    # Chuyển đổi data thành bytes
    hmac_sha256 = hmac.new(key, message, hashlib.sha256)
    signature = base64.b64encode(hmac_sha256.digest()).decode('utf-8')
    return signature

def monitor_folder(repository):
    print(f"Monitoring folder: {repository}")
    event_handler = VideoUploadHandler(repository)
    observer = Observer()
    observer.schedule(event_handler, path=repository, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(3)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def start_monitoring(camera_configs):
    threads = []
    for config in camera_configs:
        # Tạo một luồng mới cho mỗi camera config
        thread = threading.Thread(target=monitor_folder, args=(config,))
        thread.start()
        threads.append(thread)

    # Đợi tất cả các luồng kết thúc
    for thread in threads:
        thread.join()
# sending a POST request
def post_request(url, files=None, json=None, headers=None):
    response = requests.post(url=url, files=files, headers=headers, json=json, verify=True)
    if response.status_code != 200:
        print(f"Request failed with status code {response.status_code}")
        print(f"Response text: {response.text}")  # In ra nội dung phản hồi từ máy chủ
        return None
    else:
        print(response.status_code)
        return response

def compute_content_hash(content):
    sha256 = hashlib.sha256()
    # Kiểm tra xem content có phải là bytes không
    if isinstance(content, str):
        content = content.encode('utf-8')  # Chuyển đổi chuỗi thành bytes nếu cần
    sha256.update(content)
    hashed_content = base64.b64encode(sha256.digest()).decode('utf-8')
    return hashed_content


def generate_signature(secret_key, data):
    key = bytes(secret_key, 'utf-8')
    message = bytes(data, 'utf-8')
    hmac_sha256 = hmac.new(key, message, hashlib.sha256)
    signature = base64.b64encode(hmac_sha256.digest()).decode('utf-8')
    return signature

def read_file(file_path):
    try:
        with open(file_path, 'rb') as file:  # Đảm bảo đọc tệp dưới dạng bytes (rb)
            content = file.read()
            return content
    except FileNotFoundError:
        print(f"The file at {file_path} was not found.")
    except IOError:
        print(f"An error occurred while reading the file at {file_path}.")

def get_file(file_path):
    try:
        files = [
            ('File', (os.path.basename(file_path), open(file_path, 'rb'), 'application/octet-stream'))
        ]
        return files
    except FileNotFoundError:
        print(f"The file at {file_path} was not found.")
    except IOError:
        print(f"An error occurred while reading the file at {file_path}.")
    return None

def get_rfc1123_date():
    now = datetime.now(timezone.utc)
    rfc1123_date = email.utils.formatdate(timeval=now.timestamp(), usegmt=True)
    print(rfc1123_date)
    return rfc1123_date

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import subprocess
import threading
import os
import torch
import pathlib
import json 
from ultralytics import YOLO
temp = pathlib.PosixPath
pathlib.PosixPath = pathlib.WindowsPath


with open('response.json', 'r', encoding='utf-8') as f:
    json_data = json.load(f)

# Extract the camera information from the JSON data
def load_rtsp_links(json_data):
    rtsp_links = []

    # Extract farm information from farm_response
    farms = json_data[0]['farm_response']['items']

    # Loop through each farm to get farm ID
    for farm in farms:
        farm_id = farm['id']

        # Extract camera information from camera_response
        cameras = json_data[1]['camera_response']['cameras']
        pen_cameras = json_data[1]['camera_response']['penCameras']

        # Add cameras to rtsp_links
        for camera in cameras:
            rtsp_links.append({
                "farmID": farm_id,
                "cameraID": camera['id'],  # Add cameraID here
                "channelID": f"Channel{camera['channelId']}",
                "rtsp": camera['url']
            })

        # Add pen cameras to rtsp_links
        for pen_camera in pen_cameras:
            rtsp_links.append({
                "farmID": pen_camera['farmId'],
                "penID": pen_camera['PenId'],  # Update to PenId
                "channelID": f"Channel{pen_camera['channelId']}",
                "rtsp": pen_camera['cameraUrl']
            })

    return rtsp_links

class RTSPManager(tk.Tk):
    def __init__(self, config):
        super().__init__()

        # Load config values
        self.config = config
        self.fps = config['fps']
        self.window_width = config['window_size']['width']
        self.window_height = config['window_size']['height']
        self.hls_time = config['hls_time']
        self.img_resize = (config['img_resize']['width'], config['img_resize']['height'])
        self.output_directory = config['output_directory']

        self.title("RTSP Stream Management")
        self.geometry(f"{self.window_width}x{self.window_height}")

        self.rtsp_links = load_rtsp_links(json_data)

        self.current_rtsp_links = []
        self.video_capture = {}
        self.video_label = {}
        self.recording = {}
        self.stop_flags = {}
        self.review_mode = {}
        self.video_writer = {}
        self.processes = {}
        self.threads = {}

        self.create_api_bar()
        self.create_video_frame()
        
        self.model_path = 'E:/kaggle_weight_chicken/v8_aug_best.pt'
        self.model = YOLO(self.model_path)

        load_dotenv()

        # Get environment variables
        self.HMAC_KEY = os.getenv("HMAC_KEY")
        self.STREAM_FARM_ENDPOINT = os.getenv("STREAM_FARM_ENDPOINT")
        self.STREAM_PEN_ENDPOINT = os.getenv("STREAM_PEN_ENDPOINT")

    def create_api_bar(self):
        # Farm dropdown
        tk.Label(self, text="Select Farm:").pack(pady=5)
        self.selected_farm = tk.StringVar(self)
        self.farm_dropdown = ttk.Combobox(self, textvariable=self.selected_farm, state="readonly")
        self.farm_dropdown['values'] = list(set([link['farmID'] for link in self.rtsp_links]))  # Unique farm IDs
        self.farm_dropdown.bind("<<ComboboxSelected>>", self.update_camera_dropdown)
        self.farm_dropdown.pack(pady=10)

        # Camera dropdown
        tk.Label(self, text="Select Camera:").pack(pady=5)
        self.selected_camera = tk.StringVar(self)
        self.camera_dropdown = ttk.Combobox(self, textvariable=self.selected_camera, state="readonly")
        self.camera_dropdown.pack(pady=10)
        self.camera_dropdown.bind("<<ComboboxSelected>>", self.add_video)

        reset_button = tk.Button(self, text="Reset All Farms", command=self.reset_farms)
        reset_button.pack(pady=10)

        upload_button = tk.Button(self, text="Upload Files to Server", command=self.upload_files_to_server)
        upload_button.pack(pady=10)
    
    def monitor_multiple_folders(self, folders: list):
        threads = []
        for folder in folders:
            thread = threading.Thread(target=monitor_folder, args=(folder,))
            thread.start()
            threads.append(thread)

        for thread in threads:
            # thread.join()
            self.threads = threads  # Store threads to manage them later if needed

    def upload_files_to_server(self):
        directories = []
        while True:
            # Open a directory selection dialog for each folder
            directory = filedialog.askdirectory(title="Select a folder (Cancel to stop)")
            if not directory:  # Break if user cancels selection
                break
            directories.append(directory)
        
        if directories:
            # Start monitoring all selected folders in parallel
            self.monitor_multiple_folders(directories)
    
    def update_camera_dropdown(self, event):
        # Get the selected farm
        selected_farm_id = self.selected_farm.get()

        # Filter cameras that belong to the selected farm
        cameras = [f"{link['channelID']}" for link in self.rtsp_links if link['farmID'] == selected_farm_id]
        cameras = list(set(cameras))

        # Update the camera dropdown
        self.camera_dropdown['values'] = cameras
        self.camera_dropdown.set('')  # Clear the selection in the camera dropdown

    def create_video_frame(self):
        self.video_frame = tk.Frame(self)
        self.video_frame.pack(pady=10, fill=tk.BOTH, expand=True)

    def add_video(self, event):
        selected_farm = self.selected_farm.get()
        selected_camera = self.selected_camera.get()

        # Get the corresponding rtsp link
        selected_link = next(link for link in self.rtsp_links if link['farmID'] == selected_farm and link['channelID'] == selected_camera)

        if selected_link not in self.current_rtsp_links and len(self.current_rtsp_links) < 6:
            self.current_rtsp_links.append(selected_link)
            self.create_video_display(selected_link)
        self.update_video_grid()

    def create_video_display(self, rtsp_info):
        video_display_frame = tk.Frame(self.video_frame, bd=2, relief=tk.SUNKEN)

        info_label = tk.Label(video_display_frame, text=f"{rtsp_info['channelID'][:15]}..." if len(rtsp_info['channelID']) > 15 else rtsp_info['channelID'], anchor=tk.W)
        info_label.grid(row=0, column=0, columnspan=3, sticky=tk.W)

        self.video_label[rtsp_info["rtsp"]] = tk.Label(video_display_frame)
        self.video_label[rtsp_info["rtsp"]].grid(row=1, column=0, columnspan=4)

        review_var = tk.BooleanVar()
        review_checkbox = tk.Checkbutton(video_display_frame, text="Review",
                                         variable=review_var,
                                         command=lambda: self.toggle_review(rtsp_info["rtsp"], review_var))
        review_checkbox.grid(row=0, column=2, sticky=tk.E)

        info_button = tk.Button(video_display_frame, text="Info", command=lambda: self.show_info(rtsp_info, info_label))
        info_button.grid(row=2, column=0, padx=5)

        record_button = tk.Button(video_display_frame, text="Record",
                                  command=lambda: self.start_recording(rtsp_info["rtsp"]))
        record_button.grid(row=2, column=1, padx=5)

        stop_record_button = tk.Button(video_display_frame, text="Stop Record", 
                                       command=lambda: self.stop_recording(rtsp_info["rtsp"]))
        stop_record_button.grid(row=2, column=2, padx=5)

        video_display_frame.info_label = info_label
        video_display_frame.rtsp = rtsp_info["rtsp"]
        self.video_label[rtsp_info["rtsp"]].video_display_frame = video_display_frame

    def update_video_grid(self):
        # Căn giữa các video
        total_videos = len(self.current_rtsp_links)
        columns = 3  # Hiển thị 3 video mỗi hàng
        for idx, rtsp_link in enumerate(self.current_rtsp_links):
            video_frame = self.video_label[rtsp_link["rtsp"]].video_display_frame

            row = idx // columns
            col = idx % columns
            video_frame.grid(row=row, column=col, padx=10, pady=10, sticky='n')

        # Điều chỉnh căn giữa frame video toàn bộ grid
        for col in range(columns):
            self.video_frame.grid_columnconfigure(col, weight=1)

    def show_info(self, rtsp_info, info_label):
        info = f"Farm ID: {rtsp_info['farmID']}\nChannel ID: {rtsp_info['channelID']}"
        info_label.config(text=info)

    def toggle_review(self, rtsp_link, review_var):
        if review_var.get():
            self.review_mode[rtsp_link] = True
            threading.Thread(target=self.open_video_stream, args=(rtsp_link,), daemon=True).start()
        else:
            self.review_mode[rtsp_link] = False
            self.clear_video_display(rtsp_link)  # Clear video when unticked
            self.stop_video_stream(rtsp_link)

    def clear_video_display(self, rtsp_link):
        # Set the video label to a blank frame (you can replace it with a placeholder image if needed)
        blank_image = ImageTk.PhotoImage(image=Image.new('RGB', (200, 150), color='white'))
        self.video_label[rtsp_link].config(image=blank_image)
        self.video_label[rtsp_link].image = blank_image

    def open_video_stream(self, rtsp_link):
        if rtsp_link in self.video_capture:
            return
        
        self.video_capture[rtsp_link] = cv2.VideoCapture(rtsp_link)

        if not self.video_capture[rtsp_link].isOpened():
            print(f"Error: Could not open video {rtsp_link}.")
            return

        self.update_frame(rtsp_link)

    def stop_video_stream(self, rtsp_link):
        if rtsp_link in self.video_capture:
            video_capture_obj = self.video_capture[rtsp_link]
            if video_capture_obj.isOpened():
                video_capture_obj.release()
                print(f"Stream for {rtsp_link} has been stopped.")
            del self.video_capture[rtsp_link]

    def update_frame(self, rtsp_link):
        if rtsp_link not in self.video_capture or not self.video_capture[rtsp_link].isOpened():
            return

        ret, frame = self.video_capture[rtsp_link].read()
        if not ret:
            print(f"Error: Could not read frame from stream {rtsp_link}.")
            self.stop_video_stream(rtsp_link)
            return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame).resize(self.img_resize)
        img_tk = ImageTk.PhotoImage(image=img)

        self.video_label[rtsp_link].config(image=img_tk)
        self.video_label[rtsp_link].image = img_tk

        if self.review_mode[rtsp_link]:
            self.after(100, lambda: self.update_frame(rtsp_link))

    def start_recording(self, rtsp_link):
        if rtsp_link not in self.video_capture or not self.video_capture[rtsp_link].isOpened():
            self.video_capture[rtsp_link] = cv2.VideoCapture(rtsp_link)

        if not self.video_capture[rtsp_link].isOpened():
            print(f"Failed to open RTSP stream: {rtsp_link}")
            return
        
        self.stop_flags[rtsp_link] = False

        if rtsp_link not in self.threads:
            self.threads[rtsp_link] = threading.Thread(target=self.record_stream, args=(rtsp_link,), daemon=True)
            self.threads[rtsp_link].start()

    # Function to compute brightness of the frame
    def calculate_brightness(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)  # Convert frame to HSV color space
        brightness = np.mean(hsv[:, :, 2])  # Mean of the V (value) channel in HSV represents brightness
        return brightness

    # Adjust brightness if needed
    def adjust_brightness(self,frame, target_brightness=150, threshold=40):
        current_brightness = self.calculate_brightness(frame)
        
        if current_brightness < target_brightness - threshold:  # If frame is too dark
            factor = target_brightness / current_brightness
            frame = cv2.convertScaleAbs(frame, alpha=factor, beta=0)  # Brighten the image
            # print("brightness increased")
        elif current_brightness > target_brightness + threshold:  # If frame is too bright
            factor = target_brightness / current_brightness
            frame = cv2.convertScaleAbs(frame, alpha=factor, beta=0)  # Darken the image
            # print("brightness decreased")


        return frame
    
    def calculate_area_in_image(self, bbox):
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        area = width * height
        return area
    
    # Hàm tính kích thước thật dựa trên khoảng cách và tiêu cự
    def calculate_real_size(self, area_in_image, distance_to_chicken, focal_length):
        real_size = area_in_image * (distance_to_chicken / focal_length)
        return real_size

    # Hàm ước tính cân nặng của gà
    def estimate_weight(self, real_size, factor, k=0.05, alpha=1.5):
        weight = k * (real_size ** alpha) * factor
        return weight
    
    def record_stream(self, rtsp_link):

        if rtsp_link not in self.video_capture or not self.video_capture[rtsp_link].isOpened():
            self.video_capture[rtsp_link] = cv2.VideoCapture(rtsp_link)

        if not self.video_capture[rtsp_link].isOpened():
            print(f"Failed to open RTSP stream: {rtsp_link}")
            return

        # Get the farmID and channelID from the RTSP link
        selected_link = next(link for link in self.rtsp_links if link['rtsp'] == rtsp_link)
        farm_id = selected_link['farmID']
        channel_id = selected_link['channelID']
        pen_id = selected_link.get('penID', None)
        if not pen_id:
            output_dir = os.path.join('./recorded', farm_id, channel_id)
        else: 
            output_dir = os.path.join('./recorded', farm_id, pen_id, channel_id)
            
        os.makedirs(output_dir, exist_ok=True)  # Create the directories if they don't exist

        # Create folder structure: farmID/channelID

        if rtsp_link not in self.video_writer:
            actual_fps = 30
            target_fps = 10
            skip_frames = int(actual_fps / target_fps) if actual_fps > target_fps else 1

            m3u8_path = os.path.join(output_dir, f'{channel_id}_output.m3u8')

            # FFmpeg command for HLS
            if pen_id: 
                base_url = f"ai/stream_pens/{farm_id}/{pen_id}/{channel_id[-1]}/"
            else:
                base_url = f"ai/stream_pens/{farm_id}/{channel_id[-1]}/"

            ffmpeg_command = [
                'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'bgr24',
                '-s', '1920x1080', '-r', str(target_fps), '-i', '-', '-c:v', 'libx264',
                '-crf', '31',  # Use CRF to control quality
                '-b:v', '500k',  # Set bitrate to control file size
                '-pix_fmt', 'yuv420p', '-preset', 'ultrafast', '-tune', 'zerolatency',
                '-f', 'hls', '-hls_time', str(self.hls_time), '-hls_list_size', '0', '-hls_flags', 'delete_segments',
                '-hls_base_url', base_url, 
                m3u8_path
            ]

            process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)
            self.recording[rtsp_link] = True
            print(f"Recording started for {rtsp_link}")

            frame_count = 0

            # Focal length and resize factor
            focal_length = 35  # Example focal length
            resize_factor = 0.5
            weights = []  # To store the weight estimations
            height_part = None  # We'll set this later once the frame size is known

            while self.recording.get(rtsp_link, False) and (not self.stop_flags[rtsp_link]):
                ret, frame = self.video_capture[rtsp_link].read()
                if not ret:
                    break
                
                # Initialize frame height and set height parts for calculating distance
                if height_part is None:
                    frame_height, frame_width = frame.shape[:2]
                    height_part = frame_height // 4

                # Skip frames to match the target FPS
                frame_count += 1
                if frame_count % skip_frames != 0:
                    continue

                # Adjust brightness
                frame = self.adjust_brightness(frame)

                # Apply YOLOv8 processing on GPU
                try:
                    results = self.model(frame, verbose=False, half = True)  # YOLOv8 model processing (runs on GPU)
                    num_boxes = len(results[0].boxes)

                    # Annotate frames with bounding boxes, object counts, and estimate weights
                    cv2.putText(frame, f'So luong ga: {num_boxes}', (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2)
                    for box in results[0].boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])  # Bounding box coordinates
                        conf = box.conf.item()  # Confidence score
                        cls = int(box.cls.item())  # Class ID
                        if conf > 0.25:  # Only annotate boxes with confidence > 0.25
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                            # Calculate the area in the image (bounding box area)
                            area_in_image = self.calculate_area_in_image((x1, y1, x2, y2))

                            # Determine the distance factor based on the position in the frame
                            if y2 <= height_part:
                                factor = 1.5
                            elif y2 <= height_part * 2:
                                factor = 1.3
                            elif y2 <= height_part * 3:
                                factor = 1.2
                            else:
                                factor = 0.5

                            # Estimate the real size and weight of the chicken
                            distance_to_chicken = 2  # Assumed distance
                            real_size = self.calculate_real_size(area_in_image, distance_to_chicken, focal_length)
                            estimated_weight = self.estimate_weight(real_size, factor)

                            # Draw the weight on the frame
                            cv2.putText(frame, f'Weight: {estimated_weight:.2f}g', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

                            # Store the estimated weight
                            weights.append(estimated_weight)

                    # Calculate and display the average weight
                    if weights:
                        avg_weight = np.mean(weights)
                        cv2.putText(frame, f'Avg Weight: {avg_weight:.2f}g', (10, frame_height - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

                        # Resize frame before displaying
                        # frame = cv2.resize(frame, (int(frame_width * resize_factor), int(frame_height * resize_factor)))

                    # Write the processed frame to FFmpeg for saving
                    process.stdin.write(frame.tobytes())

                except Exception as e:
                    print(f"Error in YOLOv8 processing for {rtsp_link}: {e}")

            m3u8_files = [f for f in os.listdir(output_dir) if f.endswith('.m3u8')]
            if not m3u8_files:
                print("No .m3u8 files found in the folder.")
                return
            
            last_file = m3u8_files[-1]
            
            # Set the destination file name
            source_path = os.path.join(output_dir, last_file)
            destination_path = os.path.join(output_dir, f'{channel_id}_final_output.m3u8')
            
            # Copy the last file and rename it
            shutil.copy2(source_path, destination_path)
            print(f"Copied and renamed {last_file} to final_output.m3u8")

            self.video_capture[rtsp_link].release()
            process.stdin.close()
            process.wait()

    def stop_recording(self, rtsp_link):
        if rtsp_link in self.recording and self.recording[rtsp_link]:
            self.recording[rtsp_link] = False
            self.stop_flags[rtsp_link] = True  # Set stop flag to True
            print(f"Stopping recording for {rtsp_link}...")

            # Wait for the thread to stop
            if rtsp_link in self.threads and self.threads[rtsp_link].is_alive():
                self.threads[rtsp_link].join()

            # Stop the video capture
            if rtsp_link in self.video_capture and self.video_capture[rtsp_link].isOpened():
                self.video_capture[rtsp_link].release()
                print(f"Released video capture for {rtsp_link}")

            # Close the ffmpeg process
            if rtsp_link in self.processes:
                self.processes[rtsp_link].stdin.close()
                self.processes[rtsp_link].terminate()
                print(f"Terminated FFmpeg process for {rtsp_link}")

    def reset_farms(self):
        # Stop all active streams
        for rtsp_link in self.current_rtsp_links:
            self.stop_video_stream(rtsp_link['rtsp'])
        
        # Clear all displayed videos
        for rtsp_link in self.video_label:
            self.clear_video_display(rtsp_link)
        
        # Reset current RTSP links
        self.current_rtsp_links = []

        for widget in self.video_frame.winfo_children():
            widget.destroy()  # Remove each child widget from the video_frame
        
        # Reset dropdowns
        self.selected_farm.set('')  # Clear the farm dropdown selection
        self.camera_dropdown.set('')  # Clear the camera dropdown selection
        self.camera_dropdown['values'] = []  # Empty camera dropdown

        # Optionally reset threads or any other states
        self.threads = {}

if __name__ == "__main__":

    # Load config from file
    with open('config.json') as f:
        config = json.load(f)

    app = RTSPManager(config)
    app.mainloop()
