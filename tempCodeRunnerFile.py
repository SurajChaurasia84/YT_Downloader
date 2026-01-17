import yt_dlp
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os

# Force yt-dlp to use ffmpeg.exe from script folder
ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe")
ydl_base_opts = {
    'ffmpeg_location': ffmpeg_path
}

# Global vars for progress
progress_var = None
status_label = None

# Progress hook for yt-dlp
def progress_hook(d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        downloaded = d.get('downloaded_bytes', 0)
        percent = int(downloaded / total * 100) if total else 0
        speed = d.get('speed', 0)
        eta = d.get('eta', 0)

        progress_var.set(percent)
        status_label.config(text=f"Downloading... {percent}% | {speed/1024:.1f} KB/s | ETA: {eta}s")
        root.update_idletasks()
    elif d['status'] == 'finished':
        progress_var.set(100)
        status_label.config(text="Processing...")

def download():
    url = url_entry.get().strip()
    save_path = path_var.get().strip()
    quality = quality_var.get()
    download_type = type_var.get()

    if not url:
        messagebox.showerror("Error", "Please enter a YouTube URL.")
        return

    if not save_path:
        save_path = os.getcwd()

    # Build yt-dlp options
    if download_type == "Video":
        format_code = {
            "360p": "bv*[vcodec^=avc1][height<=360]+ba/best[height<=360]/bestvideo[height<=360]+bestaudio/best",
            "720p": "bv*[vcodec^=avc1][height<=720]+ba/best[height<=720]/bestvideo[height<=720]+bestaudio/best",
            "1080p": "bv*[vcodec^=avc1][height<=1080]+ba/best[height<=1080]/bestvideo[height<=1080]+bestaudio/best",
            "Best": "bv*[vcodec^=avc1]+ba/bestvideo+bestaudio/best"
        }.get(quality, "bestvideo+bestaudio/best")

        ydl_opts = {
            'outtmpl': f'{save_path}/%(title)s.%(ext)s',
            'format': format_code,
            'merge_output_format': 'mp4',
            'progress_hooks': [progress_hook],
            'ignoreerrors': True,
            'retries': 5,
            'nocheckcertificate': True
        }
    else:  # Audio
        ydl_opts = {
            'outtmpl': f'{save_path}/%(title)s.%(ext)s',
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'progress_hooks': [progress_hook],
            'ignoreerrors': True,
            'retries': 5,
            'nocheckcertificate': True
        }

    ydl_opts.update(ydl_base_opts)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        messagebox.showinfo("Success", "Download completed!")
        status_label.config(text="Download completed!")
    except Exception as e:
        messagebox.showerror("Error", f"Download failed:\n{e}")
        status_label.config(text="Error occurred!")

def browse_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        path_var.set(folder_selected)

# GUI
root = tk.Tk()
root.title("YouTube Downloader")
root.geometry("500x420")

tk.Label(root, text="YouTube URL:").pack(pady=5)
url_entry = tk.Entry(root, width=50)
url_entry.pack(pady=5)

path_var = tk.StringVar()
tk.Label(root, text="Save Location:").pack(pady=5)
path_frame = tk.Frame(root)
path_frame.pack()
tk.Entry(path_frame, textvariable=path_var, width=40).pack(side=tk.LEFT, padx=5)
tk.Button(path_frame, text="Browse", command=browse_folder).pack(side=tk.LEFT)

type_var = tk.StringVar(value="Video")
tk.Label(root, text="Download Type:").pack(pady=5)
tk.OptionMenu(root, type_var, "Video", "Audio").pack()

quality_var = tk.StringVar(value="Best")
tk.Label(root, text="Video Quality:").pack(pady=5)
ttk.Combobox(root, textvariable=quality_var, values=["360p", "720p", "1080p", "Best"]).pack()

tk.Button(root, text="Download", command=download, bg="green", fg="white", font=("Arial", 12)).pack(pady=15)

# Progress bar
tk.Label(root, text="Progress:").pack()
progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(root, length=400, variable=progress_var, maximum=100)
progress_bar.pack(pady=5)

# Status
status_label = tk.Label(root, text="Idle", fg="blue")
status_label.pack(pady=5)

root.mainloop()
