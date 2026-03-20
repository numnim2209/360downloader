# gui.py
import os
import threading
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog

from panorama import (
    extract_pano_id,
    extract_image_base_url,
    download_panorama,
    save_panorama,
    sanitize_filename,
    RESOLUTIONS,
)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("360 Downloader")
        self.geometry("600x400")
        self.resizable(False, False)

        ctk.set_appearance_mode("dark")

        # URL
        ctk.CTkLabel(self, text="Google Maps URL:").pack(padx=20, pady=(20, 5), anchor="w")
        self.url_entry = ctk.CTkEntry(self, width=560, placeholder_text="Paste Google Maps link here...")
        self.url_entry.pack(padx=20)

        # Resolution
        ctk.CTkLabel(self, text="Resolution:").pack(padx=20, pady=(15, 5), anchor="w")
        self.resolution_var = ctk.StringVar(value="High (8192x4096)")
        self.resolution_menu = ctk.CTkOptionMenu(
            self, values=list(RESOLUTIONS.keys()), variable=self.resolution_var, width=560
        )
        self.resolution_menu.pack(padx=20)

        # Download folder
        ctk.CTkLabel(self, text="Download Folder:").pack(padx=20, pady=(15, 5), anchor="w")
        folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        folder_frame.pack(padx=20, fill="x")
        self.folder_entry = ctk.CTkEntry(folder_frame, width=460)
        self.folder_entry.insert(0, str(Path.home()))
        self.folder_entry.pack(side="left")
        ctk.CTkButton(folder_frame, text="Browse", width=90, command=self._browse_folder).pack(side="right")

        # Filename
        ctk.CTkLabel(self, text="Filename (without extension):").pack(padx=20, pady=(15, 5), anchor="w")
        self.filename_entry = ctk.CTkEntry(self, width=560, placeholder_text="Leave empty for auto-name from pano ID")
        self.filename_entry.pack(padx=20)

        # Download button
        self.download_btn = ctk.CTkButton(self, text="Download", width=560, command=self._start_download)
        self.download_btn.pack(padx=20, pady=(20, 5))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, width=560)
        self.progress_bar.pack(padx=20, pady=(5, 5))
        self.progress_bar.set(0)

        # Status label
        self.status_label = ctk.CTkLabel(self, text="Ready", width=560)
        self.status_label.pack(padx=20, pady=(0, 10))

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_entry.get())
        if folder:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)

    def _set_status(self, text: str):
        self.status_label.configure(text=text)

    def _start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            self._set_status("Error: Please enter a URL")
            return

        pano_id = extract_pano_id(url)
        if not pano_id:
            self._set_status("Error: Could not find panorama ID in URL")
            return

        image_base_url = extract_image_base_url(url)
        if not image_base_url:
            self._set_status("Error: Could not find image URL in link")
            return

        width, height = RESOLUTIONS[self.resolution_var.get()]
        folder = self.folder_entry.get().strip()
        if not os.path.isdir(folder):
            self._set_status("Error: Download folder does not exist")
            return

        filename = self.filename_entry.get().strip()
        if not filename:
            filename = pano_id
        filename = sanitize_filename(filename)
        filepath = os.path.join(folder, filename + ".jpg")

        if os.path.exists(filepath):
            self._set_status(f"Warning: File already exists: {filename}.jpg")
            return

        self.download_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self._set_status("Starting download...")

        thread = threading.Thread(
            target=self._download_thread, args=(image_base_url, width, height, filepath), daemon=True
        )
        thread.start()

    def _download_thread(self, image_base_url: str, width: int, height: int, filepath: str):
        def progress_cb(current, total):
            self.after(0, self._update_progress, current, total)

        try:
            image = download_panorama(image_base_url, width, height, progress_cb=progress_cb)
            self.after(0, self._set_status, "Saving image...")
            save_panorama(image, filepath)
            self.after(0, self._download_complete, filepath)
        except Exception as e:
            self.after(0, self._download_error, str(e))

    def _update_progress(self, current: int, total: int):
        self.progress_bar.set(current / total)
        self._set_status(f"Downloading image...")

    def _download_complete(self, filepath: str):
        self.progress_bar.set(1.0)
        self._set_status(f"Done! Saved to {os.path.basename(filepath)}")
        self.download_btn.configure(state="normal")

    def _download_error(self, error: str):
        self._set_status(f"Error: {error}")
        self.download_btn.configure(state="normal")
