import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from yt_dlp import YoutubeDL


class PlaylistMP3App:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Playlist → MP3")
        self.root.geometry("760x560")
        self.root.minsize(650, 480)

        self.events = queue.Queue()
        self.worker = None
        self.cancel_event = threading.Event()

        self.url_var = tk.StringVar()
        self.folder_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Music", "MP3_Downloads"))
        self.quality_var = tk.StringVar(value="192")
        self.status_var = tk.StringVar(value="Έτοιμο για λήψη.")
        self.progress_var = tk.DoubleVar(value=0)
        self.current_var = tk.StringVar(value="")

        self._build_ui()
        self.root.after(100, self._process_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="YouTube Playlist σε MP3", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="Επικόλλησε το link μιας playlist και επίλεξε πού θα αποθηκευτούν τα αρχεία."
        ).pack(anchor="w", pady=(3, 16))

        ttk.Label(outer, text="URL playlist").pack(anchor="w")
        url_row = ttk.Frame(outer)
        url_row.pack(fill="x", pady=(4, 12))
        self.url_entry = ttk.Entry(url_row, textvariable=self.url_var)
        self.url_entry.pack(fill="x", expand=True)
        self.url_entry.focus_set()

        ttk.Label(outer, text="Φάκελος αποθήκευσης").pack(anchor="w")
        folder_row = ttk.Frame(outer)
        folder_row.pack(fill="x", pady=(4, 12))
        ttk.Entry(folder_row, textvariable=self.folder_var).pack(side="left", fill="x", expand=True)
        ttk.Button(folder_row, text="Επιλογή…", command=self._choose_folder).pack(side="left", padx=(8, 0))

        options_row = ttk.Frame(outer)
        options_row.pack(fill="x", pady=(0, 14))
        ttk.Label(options_row, text="Ποιότητα MP3:").pack(side="left")
        quality = ttk.Combobox(
            options_row, textvariable=self.quality_var,
            values=("128", "192", "256", "320"), state="readonly", width=8
        )
        quality.pack(side="left", padx=(8, 4))
        ttk.Label(options_row, text="kbps").pack(side="left")

        self.start_button = ttk.Button(options_row, text="Έναρξη λήψης", command=self._start)
        self.start_button.pack(side="right")
        self.cancel_button = ttk.Button(options_row, text="Ακύρωση", command=self._cancel, state="disabled")
        self.cancel_button.pack(side="right", padx=(0, 8))

        ttk.Separator(outer).pack(fill="x", pady=(0, 12))
        ttk.Label(outer, textvariable=self.status_var).pack(anchor="w")
        ttk.Label(outer, textvariable=self.current_var).pack(anchor="w", pady=(3, 6))
        self.progress = ttk.Progressbar(outer, variable=self.progress_var, maximum=100, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 12))

        ttk.Label(outer, text="Μηνύματα").pack(anchor="w")
        log_frame = ttk.Frame(outer)
        log_frame.pack(fill="both", expand=True, pady=(4, 0))
        self.log = tk.Text(log_frame, height=10, wrap="word", state="disabled", font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(
            outer,
            text="Απαιτούνται yt-dlp και FFmpeg. Χρησιμοποίησε το εργαλείο μόνο για περιεχόμενο που δικαιούσαι να κατεβάσεις.",
            wraplength=700
        ).pack(anchor="w", pady=(10, 0))

    def _choose_folder(self):
        chosen = filedialog.askdirectory(title="Επίλεξε φάκελο αποθήκευσης")
        if chosen:
            self.folder_var.set(chosen)

    def _write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _start(self):
        url = self.url_var.get().strip()
        folder = self.folder_var.get().strip()
        if not url:
            messagebox.showwarning("Λείπει URL", "Επικόλλησε πρώτα το URL της playlist.")
            return
        if not folder:
            messagebox.showwarning("Λείπει φάκελος", "Επίλεξε φάκελο αποθήκευσης.")
            return
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Σφάλμα φακέλου", str(exc))
            return

        self.cancel_event.clear()
        self.progress_var.set(0)
        self.current_var.set("")
        self.status_var.set("Ξεκινά η λήψη…")
        self._write_log(f"Έναρξη: {url}")
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.worker = threading.Thread(
            target=self._download_worker,
            args=(url, folder, self.quality_var.get()),
            daemon=True
        )
        self.worker.start()

    def _cancel(self):
        self.cancel_event.set()
        self.status_var.set("Ζητήθηκε ακύρωση…")
        self.cancel_button.configure(state="disabled")
        self._write_log("Ζητήθηκε ακύρωση. Ολοκληρώνεται με ασφάλεια το τρέχον βήμα…")

    def _download_worker(self, url, folder, quality):
        def progress_hook(data):
            if self.cancel_event.is_set():
                raise Exception("Η λήψη ακυρώθηκε από τον χρήστη.")
            if data.get("status") == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                downloaded = data.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100) if total else 0
                name = data.get("info_dict", {}).get("title", "Λήψη αρχείου")
                self.events.put(("progress", percent, name))
            elif data.get("status") == "finished":
                self.events.put(("log", "Ολοκληρώθηκε η λήψη ήχου· γίνεται μετατροπή σε MP3…"))

        def logger_message(message):
            self.events.put(("log", message))

        options = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(folder, "%(playlist_index)03d - %(title)s.%(ext)s"),
            "noplaylist": False,
            "ignoreerrors": True,
            "windowsfilenames": True,
            "retries": 3,
            "progress_hooks": [progress_hook],
            "logger": type("QueueLogger", (), {
                "debug": lambda _self, msg: None,
                "warning": lambda _self, msg: self.events.put(("log", "Προειδοποίηση: " + str(msg))),
                "error": lambda _self, msg: self.events.put(("log", "Σφάλμα: " + str(msg))),
            })(),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }],
            "download_archive": os.path.join(folder, "downloaded.txt"),
            "noprogress": True,
        }

        try:
            with YoutubeDL(options) as ydl:
                ydl.download([url])
            if self.cancel_event.is_set():
                self.events.put(("done", "Η διαδικασία ακυρώθηκε."))
            else:
                self.events.put(("done", "Η διαδικασία ολοκληρώθηκε. Έλεγξε τον φάκελο αποθήκευσης."))
        except Exception as exc:
            self.events.put(("failed", str(exc)))

    def _process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "progress":
                    _, percent, name = event
                    self.progress_var.set(max(0, min(100, percent)))
                    self.current_var.set(name)
                    self.status_var.set(f"Λήψη σε εξέλιξη… {percent:.1f}% του τρέχοντος αρχείου")
                elif kind == "log":
                    self._write_log(event[1])
                elif kind == "done":
                    self.status_var.set(event[1])
                    self._write_log(event[1])
                    self._reset_buttons()
                elif kind == "failed":
                    self.status_var.set("Η λήψη σταμάτησε λόγω σφάλματος.")
                    self._write_log("Σφάλμα: " + event[1])
                    self._reset_buttons()
                    messagebox.showerror(
                        "Σφάλμα λήψης",
                        "Δεν ολοκληρώθηκε η λήψη.\n\nΒεβαιώσου ότι το yt-dlp είναι ενημερωμένο και ότι το FFmpeg είναι εγκατεστημένο.\n\n" + event[1]
                    )
        except queue.Empty:
            pass
        self.root.after(100, self._process_events)

    def _reset_buttons(self):
        self.start_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.worker = None

    def _on_close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno("Έξοδος", "Η λήψη είναι σε εξέλιξη. Θέλεις να ζητήσεις ακύρωση και να κλείσεις;"):
                return
            self.cancel_event.set()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PlaylistMP3App(root)
    root.mainloop()
