# main.py

import tkinter as tk
from gui_components import M3U8ConverterApp

def main():
    root = tk.Tk()
    app = M3U8ConverterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
