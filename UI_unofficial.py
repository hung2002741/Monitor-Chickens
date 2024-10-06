import os
import time
import requests
import hmac
import hashlib
import base64
from datetime import datetime, timezone
import email.utils
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import subprocess
import threading
import os
import pathlib
import json 
from ultralytics import YOLO
temp = pathlib.PosixPath
pathlib.PosixPath = pathlib.WindowsPath

# Load environment variables
load_dotenv()

# Get environment variables
HMAC_KEY = os.getenv("HMAC_KEY")
STREAM_FARM_ENDPOINT = os.getenv("STREAM_FARM_ENDPOINT")
STREAM_PEN_ENDPOINT = os.getenv("STREAM_PEN_ENDPOINT")

class VideoUploadHandler(FileSystemEventHandler):
    def __init__(self, repository : dict):
        self.repository = repository

    def on_created(self, event):
        print(f"New video detected: {event.src_path}")
        if event.is_directory:
            return None
        # Only upload m3u8 + ts files
        if not event.src_path.endswith(".m3u8") and not event.src_path.endswith(".ts"):
            return None
        # Upload the new video
        self.upload_video(event.src_path)
    # def on_moved(self, event: DirMovedEvent | FileMovedEvent) -> None:
    #     return super().on_moved(event)

    def upload_video(self, videoFilePath):
        folders = self.repository.split('/')

        farmId = folders[-2]
        channelId = folders[-1][-1]
        print(videoFilePath)
        print(farmId)
        print(channelId)
        # penId = self.repository.get("penId", None)  # penId is optional

        # Read the video file as binary
        content = read_file(videoFilePath)

        # Ensure content is not None
        if content is None:
            print(f"Error reading file: {videoFilePath}")
            return

        # Compute the content hash
        contentHash = compute_content_hash(content)

        # Format the current UTC time according to RFC1123
        timestamp_header = get_rfc1123_date()

        # Sign data with the following format
        dataToSign = f'{timestamp_header}\n{contentHash}'

        # Generate the signature
        signature = generate_signature(HMAC_KEY, dataToSign)

        # Create the API URL
        if None:
            post_url = f"{STREAM_PEN_ENDPOINT}/{farmId}/{channelId}/{penId}"
        else:
            post_url = f"{STREAM_FARM_ENDPOINT}/{farmId}/{channelId}"

        # Headers that need to be sent with the request
        headers = {
            'Authorization': f'Hmac {signature}',
            'x-ms-date': timestamp_header,
            'x-ms-content-sha256': contentHash,
        }

        # Check if the file is a .m3u8 or .ts file and set the upload accordingly
        if videoFilePath.endswith(".m3u8"):
            print(f"Uploading .m3u8 file: {videoFilePath}")
            post_request(post_url, get_file(videoFilePath), headers=headers)
        elif videoFilePath.endswith(".ts"):
            print(f"Uploading .ts file: {videoFilePath}")
            post_request(post_url, get_file(videoFilePath), headers=headers)
        else:
            print("Unsupported file format.")

def monitor_folder(repository : str):
    print(f"Monitoring folder: {repository}")
    event_handler = VideoUploadHandler(repository)
    observer = Observer()
    observer.schedule(event_handler, path=repository, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# sending a POST request
def post_request(url, files=None, json=None, headers=None):
    if files is None:
        print(f"No files to upload for {url}")
        return
    response = requests.post(url=url, files=files, headers=headers, json=json, verify=True)
    if response.status_code != 200:
        print(f"Request failed with status code {response.status_code}")
        print(response.text)
        return None
    else:
        print(response.status_code)
        return response

def compute_content_hash(content):
    sha256 = hashlib.sha256()
    # check if content is already in bytes
    if isinstance(content, str):
        content = bytes(content, 'utf-8')
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
        with open(file_path, 'rb') as file:
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

with open('response1.json', 'r', encoding='utf-8') as f:
    json_data = json.load(f)

# Extract the camera information from the JSON data
def load_rtsp_links():
    rtsp_links = []

    # Extract farm information from streams_farms_response
    farm_data = json_data[1]['streams_farms_response']['items'][0]
    farm_id = farm_data['id']

    # Extract camera information from camera_response
    cameras = json_data[2]['camera_response']['cameras']
    pen_cameras = json_data[2]['camera_response']['penCameras']

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
            "cameraID": pen_camera['id'],  # Add cameraID here
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

        self.rtsp_links = load_rtsp_links()

        self.current_rtsp_links = []
        self.video_capture = {}
        self.video_label = {}
        self.recording = {}
        self.stop_flag = False
        self.review_mode = {}
        self.video_writer = {}
        self.processes = {}
        self.threads = {}

        self.create_api_bar()
        self.create_video_frame()
        
        self.model_path = 'E:/kaggle_weight_chicken/yolov8_best.pt'
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
            thread.join()

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

        if rtsp_link not in self.threads:
            self.threads[rtsp_link] = threading.Thread(target=self.record_stream, args=(rtsp_link,), daemon=True)
            self.threads[rtsp_link].start()

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
        camera_id = selected_link.get('cameraID', 'default_camera')  # Use 'default_camera' if cameraID is not available

        # Create folder structure: farmID/channelID
        output_dir = os.path.join('./recorded', farm_id, channel_id)
        os.makedirs(output_dir, exist_ok=True)  # Create the directories if they don't exist

        if rtsp_link not in self.video_writer:
            actual_fps = 30
            target_fps = 10
            skip_frames = int(actual_fps / target_fps) if actual_fps > target_fps else 1

            m3u8_path = os.path.join(output_dir, 'output.m3u8')

            # FFmpeg command for HLS
            base_url = f"ai/stream_pens/{farm_id}/{camera_id}/{channel_id[-1]}/"

            # FFmpeg command for HLS with hls_base_url
            ffmpeg_command = [
            'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'bgr24',
            '-s', '1920x1080', '-r', str(target_fps), '-i', '-', '-c:v', 'libx264',
            '-crf', '28',  # Use CRF to control quality
            '-b:v', '500k',  # Set bitrate to control file size
            '-pix_fmt', 'yuv420p', '-preset', 'ultrafast', '-tune', 'zerolatency',
            '-f', 'hls', '-hls_time', "5", '-hls_list_size', '0', '-hls_flags', 'delete_segments',
            '-hls_base_url', base_url, 
            m3u8_path
            #str(self.hls_time)
                ]
            
            process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)
            self.recording[rtsp_link] = True
            print(f"Recording started for {rtsp_link}")

            frame_count = 0

            while self.recording.get(rtsp_link, False) and not self.stop_flag:
                ret, frame = self.video_capture[rtsp_link].read()
                if not ret:
                    break

                # Skip frames to match the target FPS
                frame_count += 1
                if frame_count % skip_frames != 0:
                    continue

                # Apply YOLOv8 processing on GPU
                try:
                    results = self.model(frame, verbose=False)  # YOLOv8 model processing (runs on GPU)
                    num_boxes = len(results[0].boxes)

                    # Annotate frames with bounding boxes and object counts
                    cv2.putText(frame, f'So luong ga: {num_boxes}', (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2)
                    for box in results[0].boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])  # Bounding box coordinates
                        conf = box.conf.item()  # Confidence score
                        cls = int(box.cls.item())  # Class ID
                        if conf > 0.25:  # Only annotate boxes with confidence > 0.25
                            label = f"{self.model.names[cls]} {conf:.2f}"
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                    # Write the processed frame to FFmpeg for saving
                    process.stdin.write(frame.tobytes())

                except Exception as e:
                    print(f"Error in YOLOv8 processing for {rtsp_link}: {e}")

            self.video_capture[rtsp_link].release()
            process.stdin.close()
            process.wait()

    def stop_recording(self, rtsp_link):
        if rtsp_link in self.recording and self.recording[rtsp_link]:
            self.recording[rtsp_link] = False
            print(f"Stopped recording for {rtsp_link}.")

    def reset_farms(self):
        for link in self.current_rtsp_links:
            rtsp_link = link["rtsp"]  # Extract the RTSP URL from the dictionary
            self.stop_video_stream(rtsp_link)
            self.stop_recording(rtsp_link)

        self.current_rtsp_links = []
        
        # Destroy all video widgets in the frame to reset the display
        for widget in self.video_frame.winfo_children():
            widget.destroy()

if __name__ == "__main__":

    # Load config from file
    with open('config.json') as f:
        config = json.load(f)

    app = RTSPManager(config)
    app.mainloop()
