# url_manager.py

class URLManager:
    def __init__(self, filename="url_log.txt"):
        self.filename = filename

    def save_url(self, url):
        if not self.url_exists(url):
            with open(self.filename, "a") as file:
                file.write(url + "\n")

    def load_urls(self):
        try:
            with open(self.filename, "r") as file:
                return file.readlines()
        except FileNotFoundError:
            return []

    def url_exists(self, url):
        urls = self.load_urls()
        return url in (url.strip() for url in urls)
