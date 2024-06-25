# ytDlp.py

import yt_dlp
import os
import logging
import speech_recognition as sr

class YoutubeDLTask:
    def __init__(self, url, output_dir, format, update_text_widget, completion_callback):
        self.url = url
        self.output_dir = output_dir
        self.format = format
        self.update_text_widget = update_text_widget
        self.completion_callback = completion_callback

    def run(self):
        try:
            ydl_opts = {
                'format': 'bestaudio/best' if self.format in ['mp3', 'm4a'] else 'best',
                'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'logger': YTLogger(self.update_text_widget),
            }
            if self.format == 'mp3':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            elif self.format == 'm4a':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                    'preferredquality': '192',
                }]
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(self.url, download=True)
                file_path = ydl.prepare_filename(info_dict)
                if self.format in ['mp3', 'm4a']:
                    file_path = file_path.rsplit('.', 1)[0] + '.' + self.format
                self.transcribe_audio(file_path)
            self.completion_callback(True)
        except Exception as e:
            logging.error(f"Exception during YouTube download: {e}")
            self.update_text_widget(f"Error: {e}\n")
            self.completion_callback(False)

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            progress_string = f"[download] {d['_percent_str']} of {d['_total_bytes_str']} at {d['_speed_str']} ETA {d['_eta_str']}\n"
            self.update_text_widget(progress_string)

    def transcribe_audio(self, file_path):
        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(file_path) as source:
                audio = recognizer.record(source)
            self.update_text_widget(f"Transcribing audio file: {file_path}\n")
            text = recognizer.recognize_google(audio)
            self.update_text_widget(f"Transcription:\n{text}\n")
        except Exception as e:
            logging.error(f"Exception during transcription: {e}")
            self.update_text_widget(f"Error: {e}\n")

class YTLogger:
    def __init__(self, update_text_widget):
        self.update_text_widget = update_text_widget

    def debug(self, msg):
        self.update_text_widget(f"[debug] {msg}\n")

    def warning(self, msg):
        self.update_text_widget(f"[warning] {msg}\n")

    def error(self, msg):
        self.update_text_widget(f"[error] {msg}\n")
