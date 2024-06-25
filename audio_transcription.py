# audio_transcription.py

import speech_recognition as sr
import subprocess
import os
import logging

class AudioTranscriptionTask:
    def __init__(self, audio_file, update_text_widget, completion_callback, update_status_widget):
        self.audio_file = audio_file
        self.update_text_widget = update_text_widget
        self.completion_callback = completion_callback
        self.update_status_widget = update_status_widget

    def run(self):
        self.update_status_widget("Converting audio file to WAV format...")
        wav_file = self.convert_to_wav(self.audio_file)
        if wav_file:
            self.update_status_widget("Transcribing audio file...")
            self.transcribe_audio(wav_file)
        else:
            self.update_text_widget(f"Error: Failed to convert {self.audio_file} to WAV format.\n")
            self.update_status_widget("Conversion failed.")
            self.completion_callback(False)

    def convert_to_wav(self, input_file):
        try:
            output_file = input_file.rsplit('.', 1)[0] + '.wav'
            command = ['ffmpeg', '-y', '-i', input_file, output_file]
            subprocess.run(command, check=True)
            return output_file
        except subprocess.CalledProcessError as e:
            logging.error(f"Error converting file {input_file} to WAV: {e}")
            return None

    def transcribe_audio(self, file_path):
        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(file_path) as source:
                audio = recognizer.record(source)
            self.update_text_widget(f"Transcribing audio file: {file_path}\n")
            text = recognizer.recognize_google(audio)
            self.update_text_widget(f"Transcription:\n{text}\n")
            self.update_status_widget("Transcription complete.")
            self.completion_callback(True)
        except Exception as e:
            logging.error(f"Exception during transcription: {e}")
            self.update_text_widget(f"Error: {e}\n")
            self.update_status_widget("Transcription failed.")
            self.completion_callback(False)
