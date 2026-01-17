import os
os.environ["KIVY_GL_BACKEND"] = "angle_sdl2"

import platform
import threading
import yt_dlp
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.progressbar import ProgressBar
from kivy.core.window import Window
from kivy.clock import Clock

# Window size for desktop testing
Window.size = (360, 640)

# Default save path (Windows vs Android)
if platform.system() == "Windows":
    default_path = os.path.join(os.path.expanduser("~"), "Downloads")
else:
    default_path = "/storage/emulated/0/Download"

# ffmpeg path (for Windows desktop)
ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe")
ydl_base_opts = {'ffmpeg_location': ffmpeg_path}


class DownloaderLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=10, padding=15, **kwargs)

        # URL input
        self.add_widget(Label(text="YouTube URL:", size_hint=(1, None), height=30))
        self.url_input = TextInput(hint_text="Enter YouTube URL", size_hint=(1, None), height=40)
        self.add_widget(self.url_input)

        # Save location
        self.add_widget(Label(text="Save Location:", size_hint=(1, None), height=30))
        path_box = BoxLayout(orientation="horizontal", size_hint=(1, None), height=40, spacing=5)
        self.path_input = TextInput(text=default_path)
        path_box.add_widget(self.path_input)
        browse_btn = Button(text="Browse", size_hint=(None, 1), width=100)
        browse_btn.bind(on_press=self.open_filechooser)
        path_box.add_widget(browse_btn)
        self.add_widget(path_box)

        # Download type
        self.add_widget(Label(text="Download Type:", size_hint=(1, None), height=30))
        self.type_spinner = Spinner(text="Video", values=["Video", "Audio"], size_hint=(1, None), height=40)
        self.add_widget(self.type_spinner)

        # Video quality
        self.add_widget(Label(text="Video Quality:", size_hint=(1, None), height=30))
        self.quality_spinner = Spinner(text="Best", values=["360p", "720p", "1080p", "Best"], size_hint=(1, None), height=40)
        self.add_widget(self.quality_spinner)

        # Progress + status at bottom
        self.progress_bar = ProgressBar(max=100, value=0, size_hint=(1, None), height=30)
        self.progress_label = Label(text="Progress: 0%", size_hint=(1, None), height=30)
        self.status_label = Label(text="", size_hint=(1, None), height=30, color=(1, 0, 0, 1))

        # Initially hide progress
        self.progress_bar.opacity = 0
        self.progress_label.opacity = 0

        self.add_widget(self.progress_bar)
        self.add_widget(self.progress_label)
        self.add_widget(self.status_label)

        # Download button
        self.download_btn = Button(text="Download", background_color=(0, 1, 0, 1), size_hint=(1, None), height=50)
        self.download_btn.bind(on_press=self.start_download)
        self.add_widget(self.download_btn)

    # Folder chooser
    def open_filechooser(self, instance):
        chooser_layout = BoxLayout(orientation="vertical")
        chooser = FileChooserListView(path=self.path_input.text, dirselect=True)
        chooser_layout.add_widget(chooser)
        btns = BoxLayout(size_hint=(1, None), height=50)
        select_btn = Button(text="Select")
        cancel_btn = Button(text="Cancel")
        btns.add_widget(select_btn)
        btns.add_widget(cancel_btn)
        chooser_layout.add_widget(btns)

        from kivy.uix.popup import Popup
        popup = Popup(title="Choose Folder", content=chooser_layout, size_hint=(0.9, 0.9))

        def select_folder(instance):
            if chooser.selection:
                self.path_input.text = chooser.selection[0]
                popup.dismiss()

        select_btn.bind(on_press=select_folder)
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        popup.open()

    def start_download(self, instance):
        url = self.url_input.text.strip()
        save_path = self.path_input.text.strip()
        quality = self.quality_spinner.text
        download_type = self.type_spinner.text

        if not url:
            self.update_status("Please enter a YouTube URL.")
            return
        if not url.startswith("http"):
            self.update_status("Invalid URL.")
            return
        if not save_path:
            save_path = default_path

        # Reset & show progress
        self.update_progress(0)
        self.progress_bar.opacity = 1
        self.progress_label.opacity = 1
        self.update_status("Starting download...")

        # Disable button while downloading
        self.download_btn.disabled = True

        # Run download in separate thread
        threading.Thread(target=self.download_video, args=(url, save_path, quality, download_type)).start()

    def download_video(self, url, save_path, quality, download_type):
        def progress_hook(d):
            if d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    percent_val = (downloaded / total) * 100
                    Clock.schedule_once(lambda dt: self.update_progress(percent_val))
            elif d['status'] == 'finished':
                Clock.schedule_once(lambda dt: self.update_status("Downloading..."))

        try:
            if download_type == "Video":
                format_code = {
                    "360p": "bv*[vcodec^=avc1][height<=360]+ba/best[height<=360]",
                    "720p": "bv*[vcodec^=avc1][height<=720]+ba/best[height<=720]",
                    "1080p": "bv*[vcodec^=avc1][height<=1080]+ba/best[height<=1080]",
                    "Best": "bv*[vcodec^=avc1]+ba/best"
                }.get(quality, "bv*[vcodec^=avc1]+ba/best")

                ydl_opts = {
                    'outtmpl': f'{save_path}/%(title)s.%(ext)s',
                    'format': format_code,
                    'merge_output_format': 'mp4',
                    'progress_hooks': [progress_hook]
                }
            else:
                ydl_opts = {
                    'outtmpl': f'{save_path}/%(title)s.%(ext)s',
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'progress_hooks': [progress_hook]
                }

            ydl_opts.update(ydl_base_opts)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            Clock.schedule_once(lambda dt: self.update_status("Download completed!"))
            Clock.schedule_once(lambda dt: self.update_progress(100))
        except Exception as e:
            Clock.schedule_once(lambda dt: self.update_status(f"Error: {e}"))
        finally:
            Clock.schedule_once(lambda dt: self.enable_button())

    # UI updates
    def update_progress(self, value):
        self.progress_bar.value = value
        self.progress_label.text = f"Progress: {int(value)}%"

    def update_status(self, message):
        self.status_label.text = message

    def enable_button(self):
        self.download_btn.disabled = False


class YouTubeDownloaderApp(App):
    def build(self):
        return DownloaderLayout()


if __name__ == '__main__':
    YouTubeDownloaderApp().run()
