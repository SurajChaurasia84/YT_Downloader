import os
os.environ["KIVY_GL_BACKEND"] = "angle_sdl2"

import re
import threading
import yt_dlp
from kivy.clock import Clock
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.filemanager import MDFileManager
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivymd.uix.menu import MDDropdownMenu

# KV UI
KV = '''
BoxLayout:
    orientation: "vertical"
    spacing: dp(10)
    padding: dp(15)
    size_hint: 1, 1

    MDTextField:
        id: url_input
        hint_text: "Enter YouTube URL"
        helper_text: "Paste the video or playlist link"
        helper_text_mode: "on_focus"
        size_hint_y: None
        height: dp(55)
        font_size: app.font_size

    MDRaisedButton:
        text: "Choose Save Folder"
        size_hint_y: None
        height: dp(50)
        on_release: app.file_manager_open()

    MDLabel:
        id: save_path_label
        text: "Save To: " + app.save_path
        halign: "left"
        font_size: app.font_size

    MDLabel:
        text: "Download Type"
        halign: "left"
        font_size: app.font_size
    MDDropDownItem:
        id: type_dropdown
        text: "Video"
        on_release: app.menu_type.open()

    MDLabel:
        id: quality_label
        text: "Video Quality"
        halign: "left"
        font_size: app.font_size
    MDDropDownItem:
        id: quality_dropdown
        text: "Best"
        on_release: app.menu_quality.open()

    MDRaisedButton:
        text: "Download"
        size_hint_y: None
        height: dp(55)
        md_bg_color: app.theme_cls.primary_color
        on_release: app.start_download_thread()

    MDProgressBar:
        id: progress_bar
        value: 0
        size_hint_y: None
        height: dp(12)
        opacity: 1

    MDLabel:
        id: status_label
        text: "Idle"
        halign: "center"
        theme_text_color: "Secondary"
        font_size: app.font_size
'''

class YouTubeDownloaderApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Green"
        self.save_path = os.getcwd()
        self.font_size = sp(16)
        self.file_manager = MDFileManager(
            exit_manager=self.file_manager_close,
            select_path=self.select_path,
            preview=False
        )
        self.screen = Builder.load_string(KV)

        # Menus for type and quality
        self.menu_type = MDDropdownMenu(
            caller=self.screen.ids.type_dropdown,
            items=[{"text": t, "on_release": lambda x=t: self.set_type(x)} for t in ["Video", "Audio"]],
            width_mult=3,
        )
        self.video_qualities = ["360p", "720p", "1080p", "Best"]
        self.audio_qualities = ["128kbps", "192kbps", "320kbps"]
        self.update_quality_menu("Video")

        Window.bind(on_resize=self.adjust_layout)
        return self.screen

    # ---------- Layout ----------
    def adjust_layout(self, *args):
        width, _ = Window.size
        self.font_size = sp(14 if width < 500 else 16)
        self.screen.padding = dp(10 if width < 500 else 20)

    # ---------- File Manager ----------
    def file_manager_open(self):
        self.file_manager.show(os.getcwd())
    def file_manager_close(self, *args):
        self.file_manager.close()
    def select_path(self, path):
        self.save_path = path
        self.screen.ids.save_path_label.text = f"Save To: {path}"
        self.file_manager_close()

    # ---------- Menus ----------
    def set_type(self, value):
        self.screen.ids.type_dropdown.set_item(value)
        self.menu_type.dismiss()
        self.update_quality_menu(value)
    def set_quality(self, value):
        self.screen.ids.quality_dropdown.set_item(value)
        self.menu_quality.dismiss()
    def update_quality_menu(self, type_value):
        if type_value == "Video":
            qualities = self.video_qualities
            self.screen.ids.quality_label.text = "Video Quality"
        else:
            qualities = self.audio_qualities
            self.screen.ids.quality_label.text = "Audio Quality"
        self.menu_quality = MDDropdownMenu(
            caller=self.screen.ids.quality_dropdown,
            items=[{"text": q, "on_release": lambda x=q: self.set_quality(x)} for q in qualities],
            width_mult=3,
        )
        self.screen.ids.quality_dropdown.set_item(qualities[-1])

    # ---------- Progress ----------
    def update_progress(self, value, status):
        self.screen.ids.progress_bar.value = value
        self.screen.ids.status_label.text = status
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            percent = int(downloaded / total * 100) if total else 0
            Clock.schedule_once(lambda dt: self.update_progress(percent, f"Downloading... {percent}%"))
        elif d['status'] == 'finished':
            Clock.schedule_once(lambda dt: self.update_progress(100, "Processing..."))

    # ---------- Download ----------
    def start_download_thread(self):
        threading.Thread(target=self.start_download).start()

    def start_download(self):
        url = self.screen.ids.url_input.text.strip()
        if not url:
            Clock.schedule_once(lambda dt: self.update_progress(0, "Please enter URL"))
            return

        download_type = self.screen.ids.type_dropdown.text
        quality = self.screen.ids.quality_dropdown.text
        ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe")

        if download_type == "Video":
            format_code = {
                "360p": "bv*[vcodec^=avc1][height<=360]+ba/best[height<=360]",
                "720p": "bv*[vcodec^=avc1][height<=720]+ba/best[height<=720]",
                "1080p": "bv*[vcodec^=avc1][height<=1080]+ba/best[height<=1080]",
                "Best": "bv*[vcodec^=avc1]+ba/best"
            }.get(quality, "bv*[vcodec^=avc1]+ba/best")

            ydl_opts = {
                'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
                'format': format_code,
                'merge_output_format': 'mp4',
                'progress_hooks': [self.progress_hook],
                'ffmpeg_location': ffmpeg_path
            }
        else:  # Audio
            bitrate = quality.replace("kbps", "")
            ydl_opts = {
                'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': bitrate,
                }],
                'progress_hooks': [self.progress_hook],
                'ffmpeg_location': ffmpeg_path
            }

        try:
            self.update_progress(0, "Starting download...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            Clock.schedule_once(lambda dt: self.update_progress(100, "Download completed!"))
        except Exception as e:
            Clock.schedule_once(lambda dt, err=str(e): self.update_progress(0, f"Error: {err}"))

if __name__ == "__main__":
    YouTubeDownloaderApp().run()
