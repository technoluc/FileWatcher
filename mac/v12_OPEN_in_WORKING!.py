from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog, Listbox, Button
import json
import os
import queue
import subprocess
import time
import requests
from PIL import Image, ImageTk
import io
from threading import Timer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from mac_notifications import client
from functools import partial
from pathlib import Path

# https://chat.openai.com/share/2edf89fe-0284-49bc-8307-6321a33b9a97

# Configuration file path
config_file = os.path.expanduser("~/.LucsNewApp.json")

# Function to open a file in Finder
def open_in_finder(file_path: str) -> None:
    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"The file {file_path} does not exist.")
        return

    try:
        subprocess.run(["open", "-R", file_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error opening file in Finder: {e}")

class FileWatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FileWatcher")
        self.set_app_icon()

        # Creating a thread-safe queue for notifications
        self.notification_queue = queue.Queue()

        # Start a method in the main thread to process queued notifications
        self.root.after(100, self.process_queued_notifications)

        # Listview setup
        self.treeview = ttk.Treeview(
            root, columns=("Name", "Status", "Path"), show="headings"
        )
        self.treeview.heading("Name", text="Name")
        self.treeview.heading("Status", text="Status")
        self.treeview.heading("Path", text="Path")
        self.treeview.pack(fill=tk.BOTH, expand=True)

        # Buttons setup
        buttons_frame = tk.Frame(root)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        self.add_button = tk.Button(
            buttons_frame, text="Add", command=self.add_watcher)
        self.add_button.pack(side=tk.LEFT, padx=5)

        self.start_button = tk.Button(
            buttons_frame, text="Start", command=self.start_watcher
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(
            buttons_frame, text="Stop", command=self.stop_watcher
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.advanced_button = tk.Button(
            buttons_frame, text="Advanced", command=self.open_advanced_settings
        )
        self.advanced_button.pack(side=tk.LEFT, padx=5)

        self.remove_button = tk.Button(
            buttons_frame, text="Remove", command=self.remove_watcher
        )
        self.remove_button.pack(side=tk.LEFT, padx=5)

        # Initialize file monitoring logic
        self.observer = Observer()
        self.observer.start()
        self.watchers = {}
        self.load_config()

        # Load watchers into the view and start active watchers
        self.load_watchers_into_view()
        for folder in self.config["watched_folders"]:
            if folder["status"] == "active":
                self.add_to_observer(folder["path"])

    def process_queued_notifications(self):
        # Continuously process notifications from the queue
        while not self.notification_queue.empty():
            message, file_path = self.notification_queue.get_nowait()
            self.display_notification(message, file_path)

        # Schedule this method to be called again after some time (e.g., 100 ms)
        self.root.after(100, self.process_queued_notifications)

    def set_app_icon(self):
        url = "https://github.com/technoluc/recycle-bin-themes/raw/main/assets/TL.png"
        response = requests.get(url)
        image = Image.open(io.BytesIO(response.content))
        photo = ImageTk.PhotoImage(image)
        self.root.iconphoto(False, photo)

    def load_config(self):
        if os.path.exists(config_file):
            with open(config_file, "r") as file:
                self.config = json.load(file)
        else:
            self.config = {"watched_folders": []}

    def save_config(self):
        with open(config_file, "w") as file:
            json.dump(self.config, file, indent=4)

    def add_watcher(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            folder_name = os.path.basename(folder_path)
            self.config["watched_folders"].append(
                {
                    "name": folder_name,
                    "path": folder_path,
                    "status": "active",
                    "excluded_subfolders": [],
                }
            )
            self.save_config()
            self.add_to_observer(folder_path)
            self.load_watchers_into_view()

    def start_watcher(self):
        selected_items = self.treeview.selection()
        for item in selected_items:
            folder = self.treeview.item(item, "values")[2]
            self.add_to_observer(folder)
            self.update_watcher_status(folder, "active")
        self.save_config()
        self.load_watchers_into_view()

    def stop_watcher(self):
        selected_items = self.treeview.selection()
        for item in selected_items:
            folder = self.treeview.item(item, "values")[2]
            self.remove_from_observer(folder)
            self.update_watcher_status(folder, "inactive")
        self.save_config()
        self.load_watchers_into_view()

    def remove_watcher(self):
        selected_items = self.treeview.selection()
        for item in selected_items:
            folder = self.treeview.item(item, "values")[2]
            self.remove_from_observer(folder)
            self.config["watched_folders"] = [
                wf for wf in self.config["watched_folders"] if wf["path"] != folder
            ]
        self.save_config()
        self.load_watchers_into_view()

    def open_advanced_settings(self):
        selected_item = self.treeview.selection()
        if selected_item:
            folder_path = self.treeview.item(selected_item[0], "values")[2]
            for folder in self.config["watched_folders"]:
                if folder["path"] == folder_path:
                    dialog = EditWatcherDialog(self.root, folder)
                    self.root.wait_window(dialog)
                    self.save_config()
                    self.load_watchers_into_view()

    def load_watchers_into_view(self):
        self.treeview.delete(*self.treeview.get_children())
        for folder in self.config["watched_folders"]:
            self.treeview.insert(
                "", "end", values=(folder["name"], folder["status"], folder["path"])
            )

    def update_watcher_status(self, folder_path, status):
        for watched_folder in self.config["watched_folders"]:
            if watched_folder["path"] == folder_path:
                watched_folder["status"] = status

    def add_to_observer(self, path):
        if path not in self.watchers:
            folder_config = next(
                (f for f in self.config["watched_folders"]
                 if f["path"] == path), None
            )
            if folder_config:
                event_handler = WatcherHandler(
                folder_config.get("excluded_subfolders", []),
                self.notification_queue  # Pass the notification queue
            )
            watch = self.observer.schedule(
                    event_handler, path, recursive=True)
            self.watchers[path] = watch

    def remove_from_observer(self, path):
        if path in self.watchers:
            self.observer.unschedule(self.watchers[path])
            del self.watchers[path]

    def open_edit_dialog(self, watcher):
        dialog = EditWatcherDialog(self.root, watcher)
        self.root.wait_window(dialog)
        self.save_config()  # Now it can access the save_config method

    def display_notification(self, message, file_path):
        # Using macos-notifications to display a notification
        client.create_notification(
            title="FileWatcher Notification",
            subtitle=message,
            icon=Path(__file__).parent / "icon.png",  # Placeholder for the icon
            action_button_str="Open in Finder",
            action_callback=partial(open_in_finder, file_path=file_path),
        )

    # Function to open a file in Finder
    def open_in_finder(file_path: str) -> None:
        # Check if the file exists
        if not os.path.exists(file_path):
            print(f"The file {file_path} does not exist.")
            return

        try:
            subprocess.run(["open", "-R", file_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error opening file in Finder: {e}")


class WatcherHandler(FileSystemEventHandler):
    def __init__(self, excluded_paths, notification_queue):
        super().__init__()
        self.excluded_paths = excluded_paths
        self.notification_queue = notification_queue

        self.last_notification_time = (
            {}
        )  # Dictionary to track last notification time per file
        self.notification_delay = 2  # Delay in seconds to debounce notifications

    def on_moved(self, event):
        if self.should_send_notification(event):
            message = f'"{event.src_path}" moved to "{event.dest_path}"'
            # Pass event.dest_path instead of event.src_path
            self.queue_notification(message, event.dest_path)

    def on_created(self, event):
        if self.should_send_notification(event):
            message = f'"{event.src_path}" was created'
            self.display_notification(message, event.src_path)

    def on_deleted(self, event):
        if self.should_send_notification(event):
            message = f'"{event.src_path}" was deleted'
            self.display_notification(message, event.src_path)

    def on_modified(self, event):
        if self.should_send_notification(event):
            message = f'"{event.src_path}" was modified'
            self.display_notification(message, event.src_path)

    def should_ignore_event(self, event):
        # Add logic to ignore certain files (temporary, system files, etc.)
        ignored_patterns = [".DS_Store", "Thumbs.db", ".tmp", "~$", "._"]
        if any(event.src_path.endswith(pattern) for pattern in ignored_patterns):
            return True
        if os.path.basename(event.src_path).startswith((".", "~")):
            return True
        for path in self.excluded_paths:
            if os.path.commonpath([event.src_path, path]) == path:
                return True
        return False

    def should_send_notification(self, event):
        # Check if the event should be ignored or debounced
        if self.should_ignore_event(event) or event.is_directory:
            return False
        current_time = time.time()
        last_time = self.last_notification_time.get(event.src_path, 0)
        if current_time - last_time < self.notification_delay:
            return False  # Debounce: too soon since the last notification
        self.last_notification_time[event.src_path] = current_time
        return True

    def queue_notification(self, message, file_path):
        # Queue the notification instead of directly displaying it
        self.notification_queue.put((message, file_path))

    def display_notification(self, message, file_path):
        # Queue the notification instead of directly displaying it
        self.notification_queue.put((message, file_path))


# Avanced Settings window
class EditWatcherDialog(tk.Toplevel):
    def __init__(self, parent, watcher):
        super().__init__(parent)
        self.watcher = watcher
        self.title("Edit Watcher")

        # Set the initial size of the window (width x height)
        self.geometry("600x400")  # Example size, adjust as needed

        # Name field
        tk.Label(self, text="Watcher Name:").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar(value=watcher["name"])
        name_entry = tk.Entry(self, textvariable=self.name_var)
        name_entry.grid(row=0, column=1, sticky="ew")

        # Listbox for excluded subfolders
        tk.Label(self, text="Excluded Subfolders:").grid(
            row=1, column=0, sticky="w")
        self.listbox = Listbox(self)
        self.listbox.grid(row=1, column=1, sticky="nsew")
        for subfolder in watcher["excluded_subfolders"]:
            self.listbox.insert(tk.END, subfolder)

        # Add and Remove buttons for subfolders
        tk.Button(self, text="Add Subfolder", command=self.add_subfolder).grid(
            row=2, column=1, sticky="ew"
        )
        tk.Button(self, text="Remove Subfolder", command=self.remove_subfolder).grid(
            row=3, column=1, sticky="ew"
        )

        # OK and Cancel buttons
        tk.Button(self, text="OK", command=self.confirm).grid(
            row=4, column=1, sticky="ew"
        )
        tk.Button(self, text="Cancel", command=self.destroy).grid(
            row=5, column=1, sticky="ew"
        )

        # Configure the grid
        self.grid_rowconfigure(1, weight=1)  # Listbox row
        self.grid_columnconfigure(1, weight=1)  # Second column

        self.resizable(True, True)  # Allow window resizing

    def add_subfolder(self):
        subfolder = filedialog.askdirectory(initialdir=self.watcher["path"])
        if subfolder:
            self.watcher["excluded_subfolders"].append(subfolder)
            self.listbox.insert(tk.END, subfolder)

    def remove_subfolder(self):
        selected_index = self.listbox.curselection()
        if selected_index:
            self.watcher["excluded_subfolders"].pop(selected_index[0])
            self.listbox.delete(selected_index)

    def confirm(self):
        self.watcher["name"] = self.name_var.get()
        self.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FileWatcherApp(root)
    root.mainloop()
