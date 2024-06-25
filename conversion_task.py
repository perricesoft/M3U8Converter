import subprocess
import re
import logging

class ConversionTask:
    def __init__(self, url, output_filename, progress_callback, completion_callback, stop_event):
        self.url = url
        self.output_filename = output_filename
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.stop_event = stop_event
        self.process = None

    def run(self):
        try:
            if self.stop_event.is_set():
                self.completion_callback(False)
                return
            command = ['ffmpeg', '-i', self.url, '-y', '-progress', 'pipe:1', '-vcodec', 'copy', '-acodec', 'copy', self.output_filename]
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})')
            duration = None
            while True:
                if self.stop_event.is_set():
                    self.process.terminate()
                    self.completion_callback(False)
                    return
                line = self.process.stdout.readline()
                if not line:
                    break
                if duration is None and "Duration" in line:
                    duration = self.get_duration_from_ffmpeg(line)
                match = time_pattern.search(line)
                if match and duration:
                    hours, minutes, seconds = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    current_seconds = hours * 3600 + minutes * 60 + seconds
                    progress = current_seconds / duration * 100
                    self.progress_callback(progress)
            self.process.wait()
            if self.process.returncode == 0:
                self.completion_callback(True)
            else:
                error_message = self.process.stdout.read()
                logging.error(f"Conversion failed for URL: {self.url} with error: {error_message}")
                self.completion_callback(False)
        except Exception as e:
            if self.process:
                self.process.terminate()
            logging.error(f"Exception during conversion: {e}")
            self.completion_callback(False)

    def get_duration_from_ffmpeg(self, line):
        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.\d{2}', line)
        if duration_match:
            hours, minutes, seconds = map(int, duration_match.groups())
            return hours * 3600 + minutes * 60 + seconds
        return None
