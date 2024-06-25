# gui_components.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from concurrent.futures import ThreadPoolExecutor
import json
import os
import pandas as pd
import threading
import queue
import logging
import subprocess
import csv

from url_manager import URLManager
from conversion_task import ConversionTask
from ytDlp import YoutubeDLTask
from audio_transcription import AudioTranscriptionTask
from transcription_tab import TranscriptionTab

logging.basicConfig(filename='conversion_errors.log', level=logging.ERROR, format='%(asctime)s:%(levelname)s:%(message)s')
SESSION_FILE = 'session.json'

class M3U8ConverterApp:
    def __init__(self, master):
        self.master = master
        master.title("M3U8 to MP4 Converter")
        self.url_manager = URLManager()
        self.bulk_conversion_active = threading.Event()
        self.stop_event = threading.Event()
        self.setup_ui()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.task_queue = queue.Queue()
        self.completed_tasks = 0
        self.total_tasks = 0
        self.load_session()
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TButton', background='#333333', foreground='white', font=('Helvetica', 10))
        self.style.configure('TLabel', font=('Helvetica', 12), padding=10)
        self.style.configure('TEntry', font=('Helvetica', 12), padding=10)
        self.style.map('TButton', background=[('active', '#555555')])
        self.style.configure('Green.Horizontal.TProgressbar', background='green', troughcolor='#333333')

        self.tab_control = ttk.Notebook(self.master)
        self.conversion_tab = ttk.Frame(self.tab_control)
        self.bulk_import_tab = ttk.Frame(self.tab_control)
        self.csv_export_tab = ttk.Frame(self.tab_control)
        self.youtube_tab = ttk.Frame(self.tab_control)
        self.transcription_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.conversion_tab, text='Convert')
        self.tab_control.add(self.bulk_import_tab, text='Bulk Import')
        self.tab_control.add(self.csv_export_tab, text='Convert to CSV')
        self.tab_control.add(self.youtube_tab, text='YouTube Download')
        self.tab_control.add(self.transcription_tab, text='Transcribe Audio')
        self.tab_control.pack(expand=1, fill="both")
        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_change)

        self.init_conversion_tab()
        self.init_bulk_import_tab()
        self.init_csv_export_tab()
        self.init_youtube_tab()
        self.init_transcription_tab()
        self.init_status_bar()

    def init_conversion_tab(self):
        conversion_frame = ttk.Frame(self.conversion_tab)
        conversion_frame.pack(padx=10, pady=10, fill="both", expand=True)

        ttk.Label(conversion_frame, text="Enter M3U8 URL:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.url_entry = ttk.Entry(conversion_frame, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(conversion_frame, text="Paste", command=self.paste_url).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(conversion_frame, text="Clear", command=lambda: self.url_entry.delete(0, tk.END)).grid(row=0, column=3, padx=5, pady=5)
        ttk.Button(conversion_frame, text="Convert to MP4", command=self.start_conversion_thread).grid(row=1, column=0, columnspan=4, padx=5, pady=5)

        self.progress = ttk.Progressbar(conversion_frame, style='Green.Horizontal.TProgressbar', orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.progress.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        self.save_path_label = ttk.Label(conversion_frame, text="")
        self.save_path_label.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky="ew")

    def init_bulk_import_tab(self):
        bulk_frame = ttk.Frame(self.bulk_import_tab)
        bulk_frame.pack(padx=10, pady=10, fill="both", expand=True)

        ttk.Label(bulk_frame, text="Bulk Import M3U8 URLs from Files or Paste:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Button(bulk_frame, text="Select Files", command=self.select_files).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Button(bulk_frame, text="Clear URLs", command=self.clear_bulk_list).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(bulk_frame, text="Folder/Base Name for Saved Files:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.folder_name_entry = ttk.Entry(bulk_frame, width=50)
        self.folder_name_entry.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        ttk.Button(bulk_frame, text="Convert All", command=self.convert_all_bulk).grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.bulk_status_label = ttk.Label(bulk_frame, text="Files remaining: 0")
        self.bulk_status_label.grid(row=6, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        self.scrollbar_bulk = ttk.Scrollbar(bulk_frame, orient=tk.VERTICAL)
        self.url_listbox_bulk = tk.Listbox(bulk_frame, yscrollcommand=self.scrollbar_bulk.set, width=60, height=10)
        self.scrollbar_bulk.config(command=self.url_listbox_bulk.yview)
        self.scrollbar_bulk.grid(row=7, column=2, sticky='ns')
        self.url_listbox_bulk.grid(row=7, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        # Add a button to delete the folder
        self.delete_folder_button = ttk.Button(bulk_frame, text="Delete Folder", command=self.delete_folder)
        self.delete_folder_button.grid(row=8, column=0, padx=5, pady=5, sticky="w")

    def init_csv_export_tab(self):
        csv_frame = ttk.Frame(self.csv_export_tab)
        csv_frame.pack(padx=10, pady=10, fill="both", expand=True)

        ttk.Label(csv_frame, text="Paste M3U8 URLs:").pack(pady=10)
        self.text_input = tk.Text(csv_frame, width=80, height=20)
        self.text_input.pack(padx=10, pady=10)
        ttk.Button(csv_frame, text="Save to CSV", command=self.save_to_csv).pack(pady=10)

    def init_youtube_tab(self):
        youtube_frame = ttk.Frame(self.youtube_tab)
        youtube_frame.pack(padx=10, pady=10, fill="both", expand=True)

        ttk.Label(youtube_frame, text="Enter YouTube URL:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.youtube_url_entry = ttk.Entry(youtube_frame, width=50)
        self.youtube_url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(youtube_frame, text="Paste", command=self.paste_youtube_url).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(youtube_frame, text="Select Format:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.youtube_format = tk.StringVar(value="video")
        format_options = ["video", "mp3", "m4a"]
        self.format_menu = ttk.OptionMenu(youtube_frame, self.youtube_format, format_options[0], *format_options)
        self.format_menu.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(youtube_frame, text="Download", command=self.start_youtube_download_thread).grid(row=2, column=0, columnspan=3, padx=5, pady=5)

        self.youtube_progress_text = tk.Text(youtube_frame, height=15, width=80, wrap=tk.WORD)
        self.youtube_progress_text.grid(row=3, column=0, columnspan=3, padx=5, pady=5)
        self.youtube_save_path_label = ttk.Label(youtube_frame, text="")
        self.youtube_save_path_label.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

    def init_transcription_tab(self):
        TranscriptionTab(self.transcription_tab)

    def init_status_bar(self):
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = tk.Label(self.master, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def update_status(self, message):
        self.master.after(0, self.status_var.set, message)

    def update_youtube_progress_text(self, message):
        self.master.after(0, self.youtube_progress_text.insert, tk.END, message)
        self.master.after(0, self.youtube_progress_text.see, tk.END)

    def paste_url(self):
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(tk.END, self.master.clipboard_get())

    def paste_youtube_url(self):
        self.youtube_url_entry.delete(0, tk.END)
        self.youtube_url_entry.insert(tk.END, self.master.clipboard_get())

    def save_to_csv(self):
        urls = self.text_input.get("1.0", tk.END).strip().split()
        if not urls:
            messagebox.showerror("Input Error", "Please paste some URLs.")
            return

        output_file = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not output_file:
            return

        try:
            df = pd.DataFrame(urls, columns=["M3U8 URLs"])
            df.to_csv(output_file, index=False)
            messagebox.showinfo("Success", f"CSV file saved as {output_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CSV file: {e}")

    def start_conversion_thread(self):
        self.progress['value'] = 0
        self.update_status("Starting conversion...")
        output_filename = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
        if output_filename:
            task = ConversionTask(
                url=self.url_entry.get(),
                output_filename=output_filename,
                progress_callback=self.update_progress,
                completion_callback=self.conversion_complete,
                stop_event=self.stop_event
            )
            self.executor.submit(task.run)
            self.delete_folder_button.config(state=tk.DISABLED)  # Disable the delete button during conversion

    def update_progress(self, progress):
        self.progress['value'] = progress
        int_progress = int(progress)
        self.update_status(f"Converting... {int_progress}% completed.")

    def conversion_complete(self, success):
        if success:
            self.save_path_label.config(text="File saved successfully.", foreground='green')
            self.url_manager.save_url(self.url_entry.get())
            self.url_entry.delete(0, tk.END)
            self.update_status("Conversion successful. Ready for next.")
        else:
            self.save_path_label.config(text="Conversion failed.", foreground='red')
            self.update_status("Conversion failed. Check logs and retry.")
            messagebox.showerror("Error", "Conversion failed. Check the log file for more details.")
        self.delete_folder_button.config(state=tk.NORMAL)  # Enable the delete button after conversion

    def start_youtube_download_thread(self):
        self.youtube_progress_text.delete("1.0", tk.END)
        self.update_status("Starting YouTube download...")
        output_dir = filedialog.askdirectory()
        if output_dir:
            task = YoutubeDLTask(
                url=self.youtube_url_entry.get(),
                output_dir=output_dir,
                format=self.youtube_format.get(),
                update_text_widget=self.update_youtube_progress_text,
                completion_callback=self.youtube_download_complete
            )
            self.executor.submit(task.run)

    def youtube_download_complete(self, success):
        if success:
            self.youtube_save_path_label.config(text="YouTube video saved successfully.", foreground='green')
            self.youtube_url_entry.delete(0, tk.END)
            self.update_status("YouTube download successful. Ready for next.")
        else:
            self.youtube_save_path_label.config(text="YouTube download failed.", foreground='red')
            self.update_status("YouTube download failed. Check logs and retry.")
            messagebox.showerror("Error", "YouTube download failed. Check the log file for more details.")

    def select_files(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("CSV files", "*.csv")])
        if file_paths:
            urls = self.extract_urls_from_files(file_paths)
            self.url_listbox_bulk.delete(0, tk.END)
            for url in urls:
                self.url_listbox_bulk.insert(tk.END, url)
            message = f"Selected {len(urls)} URLs from {'single' if len(file_paths) == 1 else 'multiple'} file(s) for conversion."
            messagebox.showinfo("Success", message)
            self.update_status(message)
        else:
            messagebox.showerror("Error", "No files were selected.")
            self.update_status("No files were selected.")

    def extract_urls_from_files(self, file_paths):
        urls = []
        for file_path in file_paths:
            try:
                if file_path.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_path)
                elif file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                else:
                    messagebox.showerror("Error", f"Unsupported file type: {file_path}")
                    continue

                # Ensure the DataFrame has at least one column
                if df.shape[1] < 1:
                    messagebox.showerror("Error", f"File {file_path} does not have the expected structure. Ensure it has at least one column.")
                    continue

                # Get URLs from the first column
                file_urls = df.iloc[:, 0].dropna().tolist()
                urls.extend(file_urls)
            except AttributeError as e:
                logging.error(f"AttributeError while processing file {file_path}: {e}")
                messagebox.showerror("Error", f"Failed to process file {file_path}: AttributeError")
            except Exception as e:
                logging.error(f"Failed to process file {file_path}: {e}")
                messagebox.showerror("Error", f"Failed to process file {file_path}: {e}")
        return urls

    def clear_bulk_list(self):
        self.url_listbox_bulk.delete(0, tk.END)
        self.folder_name_entry.delete(0, tk.END)
        self.update_status("Bulk list and input cleared.")

    def delete_folder(self):
        def remove_saved_files():
            try:
                if hasattr(self, 'save_directory') and os.path.exists(self.save_directory):
                    for root, dirs, files in os.walk(self.save_directory):
                        for file in files:
                            try:
                                os.remove(os.path.join(root, file))
                            except Exception as e:
                                logging.error(f"Error deleting file {file}: {e}")
                    for dir in dirs:
                        try:
                            os.rmdir(os.path.join(root, dir))
                        except Exception as e:
                            logging.error(f"Error deleting directory {dir}: {e}")
                    try:
                        os.rmdir(self.save_directory)
                    except Exception as e:
                        logging.error(f"Error removing directory {self.save_directory}: {e}")
            except Exception as e:
                logging.error(f"Error during file removal: {e}")
            finally:
                self.master.after(0, self.update_status, "Folder and contents deleted.")
                self.master.after(0, lambda: messagebox.showinfo("Deletion", "Folder and its contents have been deleted."))
                self.executor = ThreadPoolExecutor(max_workers=4)

        threading.Thread(target=remove_saved_files).start()
        self.update_status("Deleting folder and its contents... Please wait.")

    def convert_all_bulk(self):
        base_name = self.folder_name_entry.get().strip()
        if not base_name:
            messagebox.showerror("Error", "Please enter a valid folder/base name.")
            return

        urls = [self.url_listbox_bulk.get(idx) for idx in range(self.url_listbox_bulk.size())]
        if not urls:
            messagebox.showerror("Error", "No URLs available for conversion.")
            return

        downloads_directory = os.path.join(os.path.expanduser("~"), "Downloads")
        self.save_directory = os.path.join(downloads_directory, base_name)
        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)

        self.update_status("Processing...")
        self.bulk_conversion_active.set()
        self.stop_event.clear()
        self.delete_folder_button.config(state=tk.DISABLED)
        self.total_tasks = len(urls)
        self.completed_tasks = 0
        self.bulk_status_label.config(text=f"Files remaining: {self.total_tasks}")

        for url in urls:
            self.task_queue.put(url)

        thread = threading.Thread(target=self.bulk_convert, args=(base_name,))
        thread.start()

    def bulk_convert(self, base_name):
        file_counter = 1
        while not self.task_queue.empty() and self.bulk_conversion_active.is_set():
            url = self.task_queue.get()
            output_filename = os.path.join(self.save_directory, f"{base_name}_{file_counter}.mp4")
            task = ConversionTask(
                url=url,
                output_filename=output_filename,
                progress_callback=lambda p: self.bulk_status_label.config(text=f"Files remaining: {self.total_tasks - self.completed_tasks - 1}"),
                completion_callback=self.bulk_task_complete,
                stop_event=self.stop_event
            )
            self.executor.submit(task.run)
            file_counter += 1

    def bulk_task_complete(self, success):
        self.completed_tasks += 1
        if self.completed_tasks == self.total_tasks:
            self.update_status("Bulk conversion completed successfully.")
            self.bulk_status_label.config(text=f"Files remaining: 0")
            self.delete_folder_button.config(state=tk.NORMAL)
        elif not success:
            self.bulk_status_label.config(text=f"Files remaining: {self.total_tasks - self.completed_tasks}", foreground='red')

    def save_session(self):
        session_data = {
            'urls': [url for url in self.url_listbox_bulk.get(0, tk.END)],
        }
        with open(SESSION_FILE, 'w') as f:
            json.dump(session_data, f)

    def load_session(self):
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                session_data = json.load(f)
                for url in session_data.get('urls', []):
                    self.url_listbox_bulk.insert(tk.END, url)

    def clear_session(self):
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        self.update_status("Session cleared.")

    def on_tab_change(self, event):
        selected_tab = event.widget.tab('current')['text']
        self.update_status(f"Switched to {selected_tab} tab")

    def on_close(self):
        self.save_session()
        self.master.destroy()
