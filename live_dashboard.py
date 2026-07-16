import os
import sys
import threading
import time
from tkinter import BOTH, END, Scrollbar, Text, Tk, ttk


class LiveDashboard:
    def __init__(self):
        self.root = Tk()
        self.root.title("LogoLocator Live Action Log")
        self.root.geometry("900x500")
        self.root.minsize(700, 350)

        self.text = Text(self.root, wrap="word", font=("Consolas", 10), padx=8, pady=8)
        self.text.pack(fill=BOTH, expand=True)

        scrollbar = Scrollbar(self.root, command=self.text.yview)
        scrollbar.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=scrollbar.set)

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.is_closed = False

    def append(self, message, level="INFO"):
        if self.is_closed:
            return
        if self.root is None:
            return

        def _insert():
            self.text.insert(END, f"[{level}] {message}\n")
            self.text.see(END)
            self.root.update_idletasks()

        try:
            self.root.after(0, _insert)
        except Exception:
            _insert()

    def start(self):
        try:
            self.root.mainloop()
        except Exception:
            self.close()

    def close(self):
        self.is_closed = True
        try:
            self.root.destroy()
        except Exception:
            pass


def run_dashboard():
    dashboard = LiveDashboard()
    dashboard.append("Dashboard ready. Waiting for action logs...")
    try:
        dashboard.root.mainloop()
    except KeyboardInterrupt:
        dashboard.close()


if __name__ == "__main__":
    run_dashboard()
