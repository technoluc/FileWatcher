import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from queue import Queue
from threading import Thread
import time

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, app, notification_queue):
        self.app = app
        self.notification_queue = notification_queue
        self.changed_files = set()

    def on_modified(self, event):
        if event.is_directory:
            return

        src_path = event.src_path

        time.sleep(1)

        if src_path not in self.changed_files:
            self.changed_files.add(src_path)
            self.notification_queue.put(src_path)

class NotificationHandler(Thread):
    def __init__(self, app, notification_queue):
        super().__init__()
        self.app = app
        self.notification_queue = notification_queue
        self.daemon = True

    def run(self):
        while True:
            src_path = self.notification_queue.get()
            self.app.show_notification(f"File changed: {src_path}")

class FileWatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Luc's File Watcher App")

        self.watchers = []
        self.config_file = os.path.expanduser("~") + '/watcher_config.json'
        self.notification_queue = Queue()

        self.notification_handler = NotificationHandler(self, self.notification_queue)
        self.notification_handler.start()

        self.create_gui()
        self.load_config()
        self.update_treeview()

        self.root.protocol("WM_ICONIFY", self.on_iconify)
        self.root.protocol("WM_DEICONIFY", self.on_deiconify)
        self.minimized = False

    def create_gui(self):
        self.tree = ttk.Treeview(self.root, columns=('Status', 'Folder'))
        self.tree.heading('#0', text='Watcher')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Folder', text='Folder')

        add_button = ttk.Button(self.root, text='Add Folder', command=self.add_watcher)
        start_button = ttk.Button(self.root, text='Start Watcher', command=self.start_watcher)
        stop_button = ttk.Button(self.root, text='Stop Watcher', command=self.stop_watcher)
        remove_button = ttk.Button(self.root, text='Remove Folder', command=self.remove_watcher)

        self.tree.pack(expand=True, fill=tk.BOTH)
        add_button.pack(side=tk.LEFT)
        start_button.pack(side=tk.LEFT)
        stop_button.pack(side=tk.LEFT)
        remove_button.pack(side=tk.LEFT)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def add_watcher(self):
        folder = filedialog.askdirectory()
        if folder:
            watcher = {'folder': folder, 'status': 'started'}
            self.watchers.append(watcher)
            self.update_treeview()
            self.save_config()
            self.start_observer(len(self.watchers) - 1)

    def start_watcher(self):
        selected_item = self.tree.selection()
        if selected_item:
            index = int(selected_item[0]) - 1
            self.watchers[index]['status'] = 'started'
            self.start_observer(index)
            self.update_treeview()

    def stop_watcher(self):
        selected_item = self.tree.selection()
        if selected_item:
            index = int(selected_item[0]) - 1
            self.watchers[index]['status'] = 'stopped'
            self.stop_observer(index)
            self.update_treeview()

    def remove_watcher(self):
        selected_item = self.tree.selection()
        if selected_item:
            index = int(selected_item[0]) - 1
            del self.watchers[index]
            self.save_config()
            self.update_treeview()

    def start_observer(self, index):
        folder = self.watchers[index]['folder']
        event_handler = FileChangeHandler(self, self.notification_queue)
        observer = Observer()
        observer.schedule(event_handler, folder, recursive=True)
        observer.start()
        self.watchers[index]['observer'] = observer

    def stop_observer(self, index):
        try:
            observer = self.watchers[index]['observer']
            observer.stop()
            observer.join()
        except KeyError:
            print("Observer is not available or already stopped")

    def show_notification(self, message):
        # Lift the messagebox window to the top
        messagebox.showinfo('File Change', message)
        messagebox.lift()

    def update_treeview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, watcher in enumerate(self.watchers, start=1):
            status = watcher['status']
            folder = watcher['folder']
            self.tree.insert('', 'end', iid=str(i), text=f"Watcher {i}", values=(status, folder))

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as file:
                    self.watchers = json.load(file)

                    for i, watcher in enumerate(self.watchers, start=1):
                        status = watcher.get('status', 'stopped')
                        folder = watcher['folder']

                        if status == 'started':
                            self.start_observer(i - 1)

            else:
                print("Configuration file does not exist.")
        except json.decoder.JSONDecodeError:
            print("Error decoding JSON.")
            self.watchers = []

    def save_config(self):
        for watcher in self.watchers:
            if 'observer' in watcher:
                del watcher['observer']
        with open(self.config_file, 'w') as file:
            json.dump(self.watchers, file, indent=2)

    def on_close(self):
        self.save_config()
        self.root.destroy()

    def on_iconify(self):
        self.minimized = True

    def on_deiconify(self):
        self.minimized = False

if __name__ == "__main__":
    root = tk.Tk()
    app = FileWatcherApp(root)
    root.mainloop()
