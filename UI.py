import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import threading
import cv2
import torch
import time
from PIL import Image, ImageTk
import numpy as np
import pathlib
import subprocess
import os
import numpy as np  # To calculate average brightness


class VideoStreamApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-RTSP Stream Monitor")

        # Initialize list of RTSP streams and their AI status
        self.rtsp_urls = []
        self.ai_status = []  # List to keep track of AI detection for each RTSP stream
        self.stream_running = []  # List to track if each stream is running
        self.save_paths = []  # List to store save paths for each stream

        # RTSP file to save the URLs
        self.rtsp_file = "rtsp_links.txt"

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Set video dimensions
        self.video_width = int(screen_width / 3) - 5
        self.video_height = int(screen_height / 3) - 10

        # Frame for displaying video streams and controls
        self.video_frame = tk.Frame(root)
        self.video_frame.pack(side=tk.TOP, padx=5, pady=5)

        # Control frame for inputs
        self.control_frame = tk.Frame(root)
        self.control_frame.pack(pady=10)

        self.rtsp_listbox = tk.Listbox(self.control_frame, width=50, height=6)
        self.rtsp_listbox.pack(side=tk.LEFT)

        # Add and remove buttons
        self.add_button = tk.Button(self.control_frame, text="Thêm RTSP", command=self.add_rtsp_url)
        self.add_button.pack(side=tk.LEFT, padx=10)

        self.remove_button = tk.Button(self.control_frame, text="Xóa RTSP", command=self.remove_rtsp_url)
        self.remove_button.pack(side=tk.LEFT, padx=10)

        # Start button
        self.start_button = tk.Button(self.control_frame, text="Start Streams", command=self.start_streams)
        self.start_button.pack(side=tk.LEFT, padx=10)

        # Thread handling for streams
        self.stop_event = threading.Event()

        temp = pathlib.PosixPath
        pathlib.PosixPath = pathlib.WindowsPath
        # Load AI model
        self.model_path = './kaggle_weight_chicken/augment_best.pt'
        self.model = torch.hub.load('./yolov5', 'custom', path=self.model_path, source='local')

        # Hold references to labels and stop buttons for each stream
        self.labels = {}

        # Load RTSP URLs from file at startup
        self.load_rtsp_urls()
    def update_video_display(self):
        # Clear the current video display
        for widget in self.video_frame.winfo_children():
            widget.destroy()

        # Create new labels and checkboxes for each RTSP URL
        for index, rtsp_url in enumerate(self.rtsp_urls):
            label_original = tk.Label(self.video_frame, text=f"Video Gốc - {rtsp_url}")
            label_original.pack(anchor=tk.W)

            label_ai = tk.Label(self.video_frame, text=f"Video Qua AI - {rtsp_url}")
            label_ai.pack(anchor=tk.W)

            ai_var = tk.BooleanVar(value=self.ai_status[index])
            ai_checkbox = tk.Checkbutton(self.video_frame, text="Sử dụng AI", variable=ai_var,
                                         command=lambda idx=index: self.toggle_ai_status(idx, ai_var))
            ai_checkbox.pack(anchor=tk.W)

            # Stop button for the stream
            stop_button = tk.Button(self.video_frame, text="Dừng Stream", command=lambda idx=index: self.stop_stream(idx))
            stop_button.pack(anchor=tk.W)

            # Save directory button
            save_button = tk.Button(self.video_frame, text="Chọn thư mục lưu", command=lambda idx=index: self.choose_save_directory(idx))
            save_button.pack(anchor=tk.W)

            # Store references to the labels
            self.labels[rtsp_url] = (label_original, label_ai)
    def choose_save_directory(self, index):
    # Choose the main save directory
        save_path = filedialog.askdirectory(title="Chọn thư mục lưu video")
        if save_path:
            # Create a unique subfolder for the RTSP stream using the current timestamp
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            rtsp_subfolder = os.path.join(save_path, f"stream_{index}_{timestamp}")
            os.makedirs(rtsp_subfolder, exist_ok=True)  # Create the directory if it doesn't exist
            self.save_paths[index] = rtsp_subfolder

    def toggle_ai_status(self, index, ai_var):
        self.ai_status[index] = ai_var.get()  # Update AI status based on checkbox
        
    def add_rtsp_url(self):
        rtsp_url = simpledialog.askstring("Nhập RTSP URL", "Nhập URL RTSP:")
        if rtsp_url:
            self.rtsp_urls.append(rtsp_url)
            self.ai_status.append(False)  # Default to no AI detection
            self.stream_running.append(True)  # Start streams as running by default
            self.save_paths.append(None)  # Add placeholder for save path
            self.rtsp_listbox.insert(tk.END, rtsp_url)
            self.update_video_display()  # Update the display to include AI checkbox and stop button
            self.save_rtsp_urls()  # Save RTSP URLs to file

    def remove_rtsp_url(self):
        selected_index = self.rtsp_listbox.curselection()
        if selected_index:
            self.rtsp_urls.pop(selected_index[0])
            self.ai_status.pop(selected_index[0])  # Remove corresponding AI status
            self.stream_running.pop(selected_index[0])  # Remove corresponding stream status
            self.save_paths.pop(selected_index[0])  # Remove corresponding save path
            self.rtsp_listbox.delete(selected_index)
            self.update_video_display()
            self.save_rtsp_urls()  # Save RTSP URLs to file

    def load_rtsp_urls(self):
        """Load RTSP URLs from a file at the start of the application."""
        if os.path.exists(self.rtsp_file):
            with open(self.rtsp_file, 'r') as file:
                for line in file:
                    rtsp_url = line.strip()
                    if rtsp_url:
                        self.rtsp_urls.append(rtsp_url)
                        self.ai_status.append(False)  # Default to no AI detection
                        self.stream_running.append(True)  # Start streams as running by default
                        self.save_paths.append(None)  # Add placeholder for save path
                        self.rtsp_listbox.insert(tk.END, rtsp_url)
            self.update_video_display()

    def save_rtsp_urls(self):
        """Save the current list of RTSP URLs to a file."""
        with open(self.rtsp_file, 'w') as file:
            for rtsp_url in self.rtsp_urls:
                file.write(rtsp_url + '\n')

    def start_streams(self):
        for idx, (rtsp_url, ai) in enumerate(zip(self.rtsp_urls, self.ai_status)):
            if self.stream_running[idx]:
                threading.Thread(target=self.stream_video, args=(rtsp_url, ai, idx)).start()

    # Remaining methods like start_streams, stop_stream, stream_video, etc. stay the same
    
    def stop_stream(self, index):
        # Set the stream to not running, so it stops processing frames
        self.stream_running[index] = False
        # Clear the video frames displayed for this stream
        rtsp_url = self.rtsp_urls[index]
        self.labels[rtsp_url][0].config(image='')  # Clear original frame label
        self.labels[rtsp_url][1].config(image='')  # Clear AI frame label

    # def stream_video(self, rtsp_url, use_ai, index):
    #     cap = cv2.VideoCapture(rtsp_url)
    #     timestamp = time.strftime("%Y%m%d-%H%M%S")

    #     # Ensure the save path exists
    #     if not self.save_paths[index]:
    #         print(f"No save path set for stream {index}")
    #         return

    #     # Define the paths for saving both MP4 and M3U8 (AI and non-AI)
    #     mp4_path = f"{self.save_paths[index]}/output_{timestamp}.mp4"
    #     mp4_path_ai = f"{self.save_paths[index]}/output_ai_{timestamp}.mp4"
    #     m3u8_path = f"{self.save_paths[index]}/output_{timestamp}.m3u8"
    #     m3u8_path_ai = f"{self.save_paths[index]}/output_ai_{timestamp}.m3u8"

    #     # Initialize VideoWriter for both the original and AI processed streams
    #     video_writer = cv2.VideoWriter(mp4_path, cv2.VideoWriter_fourcc(*'H264'), 10, (self.video_width, self.video_height))
    #     video_writer_ai = None
    #     if use_ai:
    #         video_writer_ai = cv2.VideoWriter(mp4_path_ai, cv2.VideoWriter_fourcc(*'H264'), 10, (self.video_width, self.video_height))

    #     while not self.stop_event.is_set() and self.stream_running[index]:
    #         ret, frame = cap.read()
    #         if ret:
    #             # Resize frame for consistency
    #             frame = cv2.resize(frame, (self.video_width, self.video_height))

    #             # Write the original video frame
    #             video_writer.write(frame)

    #             # Process through AI if selected
    #             if use_ai:
    #                 results = self.model(frame)
    #                 num_boxes = len(results.xyxy[0])  # Get the number of detected boxes

    #                 # Write the count on the frame
    #                 cv2.putText(frame, f'So luong ga: {num_boxes}', (10, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    #                 # Draw bounding boxes on the frame
    #                 for box in results.xyxy[0]:
    #                     x1, y1, x2, y2, conf, cls = box
    #                     if conf > 0.4:  # Confidence threshold
    #                         cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 1)

    #                 # Write the AI processed frame to video
    #                 video_writer_ai.write(frame)

    #                 # Display the AI processed video
    #                 try:
    #                     self.display_frame(frame, self.labels[rtsp_url][1])
    #                 except Exception as e:
    #                     print(f"Error displaying AI frame for {rtsp_url}: {e}")
    #             else:
    #                 # Display the original video
    #                 try:
    #                     self.display_frame(frame, self.labels[rtsp_url][0])
    #                 except Exception as e:
    #                     print(f"Error displaying original frame for {rtsp_url}: {e}")

    #         else:
    #             break

    #     cap.release()
    #     video_writer.release()
    #     if video_writer_ai:
    #         video_writer_ai.release()

    #     # Convert both the saved original and AI MP4 videos to M3U8 format
    #     self.save_stream_as_m3u8(mp4_path, m3u8_path)
    #     if use_ai:
    #         self.save_stream_as_m3u8(mp4_path_ai, m3u8_path_ai)
    def stream_video(self, rtsp_url, use_ai, index):
        cap = cv2.VideoCapture(rtsp_url)
        timestamp = time.strftime("%Y%m%d-%H%M%S")

        # Ensure the save path exists
        if not self.save_paths[index]:
            print(f"No save path set for stream {index}")
            return

        # Define the paths for saving both MP4 and M3U8 (AI and non-AI)
        mp4_path = f"{self.save_paths[index]}/output_{timestamp}.mp4"
        mp4_path_ai = f"{self.save_paths[index]}/output_ai_{timestamp}.mp4"
        m3u8_path = f"{self.save_paths[index]}/output_{timestamp}.m3u8"
        m3u8_path_ai = f"{self.save_paths[index]}/output_ai_{timestamp}.m3u8"

        # Initialize VideoWriter for both the original and AI processed streams
        video_writer = cv2.VideoWriter(mp4_path, cv2.VideoWriter_fourcc(*'H264'), 10, (self.video_width, self.video_height))
        video_writer_ai = None
        if use_ai:
            video_writer_ai = cv2.VideoWriter(mp4_path_ai, cv2.VideoWriter_fourcc(*'H264'), 10, (self.video_width, self.video_height))

        # Brightness threshold and increase factor for detection
        brightness_threshold = 160  # Define the threshold for low brightness
        brightness_increase_factor = 1.4  # Factor to increase brightness

        while not self.stop_event.is_set() and self.stream_running[index]:
            ret, frame = cap.read()
            if ret:
                # Resize frame for consistency
                frame = cv2.resize(frame, (self.video_width, self.video_height))

                # Write the original video frame
                video_writer.write(frame)

                # Process through AI if selected
                if use_ai:
                    # Create a copy for detection purposes
                    detection_frame = frame.copy()

                    # Convert to grayscale to calculate average brightness
                    gray_frame = cv2.cvtColor(detection_frame, cv2.COLOR_BGR2GRAY)
                    avg_brightness = np.mean(gray_frame)

                    # If brightness is below the threshold, adjust it for detection
                    if avg_brightness < brightness_threshold:
                        hsv_frame = cv2.cvtColor(detection_frame, cv2.COLOR_BGR2HSV)
                        h, s, v = cv2.split(hsv_frame)
                        v = np.clip(v * brightness_increase_factor, 0, 255).astype(np.uint8)
                        hsv_frame = cv2.merge((h, s, v))
                        detection_frame = cv2.cvtColor(hsv_frame, cv2.COLOR_HSV2BGR)

                    # Run detection on the adjusted detection_frame
                    results = self.model(detection_frame)
                    num_boxes = len(results.xyxy[0])

                    # Annotate the original frame with detection results
                    cv2.putText(frame, f'So luong ga: {num_boxes}', (10, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                    # Draw bounding boxes on the original frame
                    for box in results.xyxy[0]:
                        x1, y1, x2, y2, conf, cls = box
                        if conf > 0.25:  # Confidence threshold
                            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 1)

                    # Write the AI processed frame to video
                    video_writer_ai.write(frame)

                    # Display the AI processed video
                    try:
                        self.display_frame(frame, self.labels[rtsp_url][1])
                    except Exception as e:
                        print(f"Error displaying AI frame for {rtsp_url}: {e}")
                else:
                    # Display the original video
                    try:
                        self.display_frame(frame, self.labels[rtsp_url][0])
                    except Exception as e:
                        print(f"Error displaying original frame for {rtsp_url}: {e}")

            else:
                break

        cap.release()
        video_writer.release()
        if video_writer_ai:
            video_writer_ai.release()

        # Convert both the saved original and AI MP4 videos to M3U8 format
        self.save_stream_as_m3u8(mp4_path, m3u8_path)
        if use_ai:
            self.save_stream_as_m3u8(mp4_path_ai, m3u8_path_ai)

    def save_stream_as_m3u8(self, mp4_path, m3u8_path):
        # Use ffmpeg to convert the stream to .m3u8 format
        ffmpeg_command = [
            'ffmpeg',
            '-i', mp4_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-f', 'hls',
            '-hls_time', '60',
            '-hls_playlist_type', 'event',
            '-hls_list_size', '0',  # Keep all segments
            m3u8_path
        ]

        # Run the ffmpeg command
        try:
            subprocess.run(ffmpeg_command, check=True)
            messagebox.showinfo("Lưu video", f"Video được lưu dưới dạng m3u8 tại: {m3u8_path}")
            os.remove(mp4_path)
        except subprocess.CalledProcessError as e:
            print(f"Error saving m3u8 video for {mp4_path}: {e}")
            messagebox.showerror("Lỗi", "Lưu video không thành công!")

    def display_frame(self, frame, label):
        frame_height, frame_width = frame.shape[:2]
        aspect_ratio = frame_width / frame_height

        if aspect_ratio > 1:  # Wide video
            new_width = self.video_width
            new_height = int(self.video_width / aspect_ratio)
        else:  # Tall video
            new_height = self.video_height
            new_width = int(self.video_height * aspect_ratio)

        frame_resized = cv2.resize(frame, (new_width, new_height))
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)

        # Update the label with the new image
        label.config(image=imgtk)
        label.image = imgtk
if __name__ == "__main__":
    root = tk.Tk()
    app = VideoStreamApp(root)
    root.mainloop()
