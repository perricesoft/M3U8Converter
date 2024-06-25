# transcription_tab.py

import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import threading
from audio_transcription import AudioTranscriptionTask

class TranscriptionTab:
    def __init__(self, parent):
        self.parent = parent
        self.audio_file_path = None

        self.restart_button = tk.Button(parent, text="Restart", command=self.restart_session, state=tk.DISABLED)
        self.restart_button.pack(pady=5)

        tk.Label(parent, text="Select an audio file (.mp3, .wav, or .m4a) and transcribe to text:").pack(pady=10)

        self.transcribe_button = tk.Button(parent, text="Select Audio File", command=self.select_file)
        self.transcribe_button.pack(pady=5)

        self.text_area = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=20, width=60)
        self.text_area.pack(pady=(0, 10), padx=10)
        self.text_area.config(state=tk.DISABLED)

        self.save_button = tk.Button(parent, text="Save Transcription", command=self.save_transcription, state=tk.DISABLED)
        self.save_button.pack(pady=5)

        self.copy_button = tk.Button(parent, text="Copy to Clipboard", command=self.copy_to_clipboard, state=tk.DISABLED)
        self.copy_button.pack(pady=5)

        self.file_type_label = tk.Label(parent, text="", fg="green")
        self.file_type_label.pack(pady=5)

        self.status_label = tk.Label(parent, text="Status: Ready", fg="blue")
        self.status_label.pack(pady=5)

    def select_file(self):
        file_path = filedialog.askopenfilename(title="Select Audio File", filetypes=[("Audio Files", "*.mp3"), ("Audio Files", "*.wav"), ("Audio Files", "*.m4a")])
        if file_path:
            self.restart_button.config(state=tk.NORMAL)
            self.transcribe_button.config(state=tk.DISABLED)
            self.update_text_area("Transcribing... Please wait.")
            file_type = file_path.split(".")[-1].upper()  # Get the file extension
            self.file_type_label.config(text=f"File Type: {file_type}")
            threading.Thread(target=self.transcribe_audio_thread, args=(file_path,)).start()

    def transcribe_audio_thread(self, audio_file_path):
        try:
            task = AudioTranscriptionTask(
                audio_file=audio_file_path,
                update_text_widget=self.update_text_area,
                completion_callback=self.transcription_callback,
                update_status_widget=self.update_status
            )
            task.run()
        except Exception as e:
            text = f"Error during transcription: {e}"
            self.update_text_area(text)
            self.transcription_callback(False)

    def transcription_callback(self, success):
        self.transcribe_button.config(state=tk.NORMAL)
        self.restart_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.NORMAL)
        self.copy_button.config(state=tk.NORMAL)
        if success:
            self.update_status("Transcription complete.")
        else:
            self.update_status("Transcription failed.")

    def update_text_area(self, text):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.INSERT, text)
        self.text_area.config(state=tk.DISABLED)
        self.text_area.see(tk.END)

    def update_status(self, status):
        self.status_label.config(text=f"Status: {status}")

    def copy_to_clipboard(self):
        try:
            self.parent.clipboard_clear()
            self.parent.clipboard_append(self.text_area.get(1.0, tk.END))
            self.parent.update()
            messagebox.showinfo("Success", "Text copied to clipboard.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy to clipboard: {e}")

    def save_transcription(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(self.text_area.get(1.0, tk.END))
                messagebox.showinfo("Success", "Transcription saved successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save transcription: {e}")

    def restart_session(self):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)
        self.copy_button.config(state=tk.DISABLED)
        self.restart_button.config(state=tk.DISABLED)
        self.update_status("Ready")
