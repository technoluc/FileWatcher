import os
import json
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class WatcherEventHandler(FileSystemEventHandler):
    def __init__(self, app, path):
        super().__init__()
        self.app = app
        self.path = path

    def on_modified(self, event):
        if event.is_directory:
            return
        self.app.show_notification(f"Map {self.path} is gewijzigd!")

class WatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Luc's Folder Watcher")

        self.watchers = []
        self.load_configuration()

        self.create_gui()

    def create_gui(self):
        self.tree = ttk.Treeview(self.root, columns=("Path", "Status"), show="headings", selectmode="browse")
        self.tree.heading("Path", text="Path")
        self.tree.heading("Status", text="Status")

        for watcher in self.watchers:
            self.tree.insert("", "end", values=(watcher["path"], "Actief" if watcher["active"] else "Inactief"))

        self.tree.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        btn_frame = ttk.Frame(self.root)
        btn_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        add_btn = ttk.Button(btn_frame, text="Voeg map toe", command=self.add_watcher)
        start_btn = ttk.Button(btn_frame, text="Start", command=self.start_watcher)
        stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_watcher)
        remove_btn = ttk.Button(btn_frame, text="Verwijder", command=self.remove_watcher)

        add_btn.grid(row=0, column=0, padx=5)
        start_btn.grid(row=0, column=1, padx=5)
        stop_btn.grid(row=0, column=2, padx=5)
        remove_btn.grid(row=0, column=3, padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def add_watcher(self):
        folder_path = filedialog.askdirectory(title="Selecteer een map om te watchen")
        if folder_path and folder_path not in [watcher["path"] for watcher in self.watchers]:
            self.watchers.append({"path": folder_path, "active": False, "observer": None})
            self.update_tree()

    def start_watcher(self):
        selected_item = self.tree.selection()
        if selected_item:
            index = int(selected_item[0][1:]) - 1
            watcher = self.watchers[index]
            path = watcher["path"]

            event_handler = WatcherEventHandler(self, path)
            observer = Observer()
            observer.schedule(event_handler, path, recursive=True)
            observer.start()

            self.watchers[index]["observer"] = observer
            self.watchers[index]["active"] = True
            self.update_tree()

    def stop_watcher(self):
        selected_item = self.tree.selection()
        if selected_item:
            index = int(selected_item[0][1:]) - 1
            watcher = self.watchers[index]
            observer = watcher.get("observer")

            if observer:
                observer.stop()
                observer.join()

            self.watchers[index]["active"] = False
            self.update_tree()

    def remove_watcher(self):
        selected_item = self.tree.selection()
        if selected_item:
            index = int(selected_item[0][1:]) - 1
            watcher = self.watchers[index]
            observer = watcher.get("observer")

            if observer:
                observer.stop()
                observer.join()

            del self.watchers[index]
            self.update_tree()

    def show_notification(self, message):
        # Hier kun je code toevoegen om meldingen te tonen
        print(message)

    def update_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, watcher in enumerate(self.watchers):
            self.tree.insert("", "end", values=(watcher["path"], "Actief" if watcher["active"] else "Inactief"))

    def load_configuration(self):
        config_file = os.path.join(os.path.expanduser("~"), "watcher_config.json")
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                self.watchers = json.load(f)

    def save_configuration(self):
        config_file = os.path.join(os.path.expanduser("~"), "watcher_config.json")
        with open(config_file, "w") as f:
            json.dump(self.watchers, f)

    def on_close(self):
        self.save_configuration()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = WatcherApp(root)
    root.mainloop()
