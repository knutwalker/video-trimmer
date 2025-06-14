#!/usr/bin/env python3

import tkinter as t
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import subprocess
import os
import threading


class VideoTrimmer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Video Trimmer")
        self.root.geometry("1200x900")

        self.video_path = None
        self.cap = None
        self.total_frames = 0
        self.fps = 30
        self.duration = 0
        self.current_frame = 0
        self.playing = False

        self.start_pos = 0
        self.end_pos = 0

        self.setup_ui()
        self.setup_keyboard_bindings()

    def setup_ui(self):
        # File selection
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=10)

        tk.Button(file_frame, text="Select Video", command=self.select_file).pack(
            side=tk.LEFT, padx=5
        )
        self.file_label = tk.Label(file_frame, text="No file selected")
        self.file_label.pack(side=tk.LEFT, padx=10)

        # Video display - larger frame for 1440p screen
        video_frame = tk.Frame(self.root)
        video_frame.pack(pady=10, expand=True, fill=tk.BOTH)

        self.video_label = tk.Label(video_frame, bg="black")
        self.video_label.pack(expand=True, fill=tk.BOTH)

        # Timeline
        timeline_frame = tk.Frame(self.root)
        timeline_frame.pack(fill=tk.X, padx=20, pady=10)

        self.timeline = tk.Scale(
            timeline_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=self.on_timeline_change,
            length=800,
        )
        self.timeline.pack(fill=tk.X)

        # Cursor controls with sync buttons
        cursor_frame = tk.Frame(self.root)
        cursor_frame.pack(pady=10)

        tk.Label(cursor_frame, text="Start:").grid(row=0, column=0, padx=5)
        self.start_scale = tk.Scale(
            cursor_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=self.update_start,
            length=300,
        )
        self.start_scale.grid(row=0, column=1, padx=5)
        self.start_time_label = tk.Label(cursor_frame, text="00:00:00")
        self.start_time_label.grid(row=0, column=2, padx=5)
        tk.Button(cursor_frame, text="Set to Current", command=self.sync_start).grid(
            row=0, column=3, padx=5
        )

        tk.Label(cursor_frame, text="End:").grid(row=1, column=0, padx=5)
        self.end_scale = tk.Scale(
            cursor_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=self.update_end,
            length=300,
        )
        self.end_scale.grid(row=1, column=1, padx=5)
        self.end_time_label = tk.Label(cursor_frame, text="00:00:00")
        self.end_time_label.grid(row=1, column=2, padx=5)
        tk.Button(cursor_frame, text="Set to Current", command=self.sync_end).grid(
            row=1, column=3, padx=5
        )

        # Controls
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10)

        tk.Button(control_frame, text="Play/Pause", command=self.toggle_play).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(control_frame, text="Process Video", command=self.process_video).pack(
            side=tk.LEFT, padx=5
        )

        # Keyboard help
        help_frame = tk.Frame(self.root)
        help_frame.pack(pady=5)
        help_text = "Keyboard: ←→ frame jump, ↑↓ 5s jump, Space play/pause"
        tk.Label(help_frame, text=help_text, font=("Arial", 9), fg="gray").pack()

    def setup_keyboard_bindings(self):
        self.root.bind("<Key>", self.on_key_press)
        self.root.focus_set()

        # Make sure the window can receive focus
        self.root.bind("<Button-1>", lambda e: self.root.focus_set())

    def on_key_press(self, event):
        if not self.cap:
            return

        if event.keysym == "Left":
            self.jump_frame(-1)
        elif event.keysym == "Right":
            self.jump_frame(1)
        elif event.keysym == "Up":
            self.jump_seconds(5)
        elif event.keysym == "Down":
            self.jump_seconds(-5)
        elif event.keysym == "space":
            self.toggle_play()

    def jump_frame(self, delta):
        new_frame = max(0, min(self.total_frames - 1, self.current_frame + delta))
        self.current_frame = new_frame
        self.timeline.set(new_frame)
        self.update_frame()

    def jump_seconds(self, seconds):
        frames_to_jump = int(seconds * self.fps)
        self.jump_frame(frames_to_jump)

    def sync_start(self):
        self.start_pos = self.current_frame
        self.start_scale.set(self.current_frame)
        self.update_time_labels()

    def sync_end(self):
        self.end_pos = self.current_frame
        self.end_scale.set(self.current_frame)
        self.update_time_labels()

    def select_file(self):
        file_path = filedialog.askopenfilename(
            initialdir=os.getcwd(),
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv")],
        )
        if file_path:
            self.load_video(file_path)

    def load_video(self, path):
        self.video_path = path
        self.file_label.config(text=os.path.basename(path))

        if self.cap:
            self.cap.release()

        # Try hardware acceleration first, fallback to software
        self.cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(path)

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.duration = self.total_frames / self.fps

        self.timeline.config(to=self.total_frames - 1)
        self.start_scale.config(to=self.total_frames - 1)
        self.end_scale.config(to=self.total_frames - 1)
        self.end_scale.set(self.total_frames - 1)

        self.update_frame()
        self.update_time_labels()

    def on_timeline_change(self, value):
        if self.cap:
            self.current_frame = int(value)
            self.update_frame()

    def update_start(self, value):
        self.start_pos = int(value)
        self.update_time_labels()

    def update_end(self, value):
        self.end_pos = int(value)
        self.update_time_labels()

    def update_time_labels(self):
        if self.cap:
            start_time = self.frame_to_time(self.start_pos)
            end_time = self.frame_to_time(self.end_pos)
            self.start_time_label.config(text=start_time)
            self.end_time_label.config(text=end_time)

    def frame_to_time(self, frame):
        seconds = frame / self.fps
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def update_frame(self):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Get video dimensions
                h, w = frame.shape[:2]

                # Calculate scaling to fit in available space while maintaining aspect ratio
                max_width = 1150
                max_height = 600

                scale_w = max_width / w
                scale_h = max_height / h
                scale = min(scale_w, scale_h)

                new_width = int(w * scale)
                new_height = int(h * scale)

                frame = cv2.resize(frame, (new_width, new_height))
                image = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(image)
                self.video_label.config(image=photo)
                self.video_label.image = photo

    def toggle_play(self):
        if not self.cap:
            return

        self.playing = not self.playing
        if self.playing:
            self.play_video()

    def play_video(self):
        if self.playing and self.cap:
            if self.current_frame < self.total_frames - 1:
                self.current_frame += 1
                self.timeline.set(self.current_frame)
                self.update_frame()
                self.root.after(int(1000 / self.fps), self.play_video)
            else:
                self.playing = False

    def process_video(self):
        if not self.video_path:
            messagebox.showerror("Error", "No video selected")
            return

        threading.Thread(target=self._process_video_thread, daemon=True).start()

    def _process_video_thread(self):
        try:
            start_time = self.frame_to_time(self.start_pos)
            end_time = self.frame_to_time(self.end_pos)

            # Run ffprobe command
            ffprobe_cmd = [
                "/opt/homebrew/bin/ffprobe",
                "-select_streams",
                "v",
                "-show_entries",
                "frame=pict_type,pts_time",
                "-of",
                "csv=p=0",
                "-skip_frame",
                "nokey",
                "-read_intervals",
                f"{start_time}%+0:02",
                "-i",
                self.video_path,
            ]

            result = subprocess.run(
                ffprobe_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            lines = result.stdout.strip().split("\n")

            if lines and lines[-1]:
                last_line = lines[-1]
                parts = last_line.split(",")
                if len(parts) >= 2:
                    pts_time = float(parts[0].strip()) - (1 / 30)

                    # Convert back to time format
                    hours = int(pts_time // 3600)
                    minutes = int((pts_time % 3600) // 60)
                    seconds = pts_time % 60
                    out_time = f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

                    # Generate output filename
                    base_name, ext = os.path.splitext(self.video_path)
                    output_file = f"{base_name}_trimmed{ext}"

                    # Run ffmpeg command
                    ffmpeg_cmd = [
                        "/opt/homebrew/bin/ffmpeg",
                        "-i",
                        self.video_path,
                        "-ss",
                        out_time,
                        "-to",
                        end_time,
                        "-map",
                        "0:v",
                        "-map",
                        "0:a",
                        "-c:v",
                        "copy",
                        "-c:a",
                        "copy",
                        "-avoid_negative_ts",
                        "1",
                        output_file,
                        "-y",
                    ]

                    subprocess.run(ffmpeg_cmd)

                    self.root.after(
                        0,
                        lambda: messagebox.showinfo(
                            "Success",
                            f"Video saved as: {os.path.basename(output_file)}",
                        ),
                    )
                else:
                    self.root.after(
                        0,
                        lambda: messagebox.showerror(
                            "Error", "Failed to parse ffprobe output"
                        ),
                    )
            else:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Error", "No keyframe found in specified range"
                    ),
                )

        except Exception as e:
            import logging

            logging.exception(e)
            error = str(e)
            self.root.after(
                0, lambda: messagebox.showerror("Error", f"Processing failed: {error}")
            )

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = VideoTrimmer()
    app.run()
