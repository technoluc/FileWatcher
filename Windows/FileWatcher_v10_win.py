import os
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from queue import Queue
from threading import Thread
from plyer import notification

# Improve: FileWatcher Menu to set notification styles,
# Single Notification style: For every file a notification is sent: on move: $filename was moved from $(dirname($src_event_path)) to $(dirname($src_event_path)). keep in mind renames should be properly handled too. 
# Current notification style: Show a single notification with a list of files changed. 
# ignore more hidden & temp files

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, app, notification_queue):
        self.app = app
        self.notification_queue = notification_queue
        self.timer_running = False
        self.timer_id = None  # Initialize timer_id

    def notify_after_delay(self):
        # Cancel the previous scheduled notification
        if self.timer_id:
            self.app.root.after_cancel(self.timer_id)
            self.timer_id = None

        src_paths = list(self.app.changed_files)
        self.notification_queue.put(src_paths)
        self.app.changed_files.clear()
        self.timer_running = False

    def ignore_file(self, file_path):
        ignored_files = ['.DS_Store', 'Thumbs.db']

        # Check if the file is hidden
        if os.name == 'nt':  # For Windows
            if os.path.basename(file_path).startswith('.') or os.path.basename(file_path).startswith('~$'):
                return True
        else:
            if file_path.startswith('.') or file_path.startswith('~$'):
                return True

        return os.path.basename(file_path) in ignored_files

    def on_modified(self, event):
        if event.is_directory:
            return self.on_created(event)

        src_path = event.src_path

        if self.ignore_file(src_path):
            return

        if src_path not in self.app.changed_files and os.path.getmtime(src_path) != os.path.getctime(src_path):
            self.app.changed_files.add(src_path)

            if not self.timer_running:
                # Schedule the notification after a delay
                self.timer_id = self.app.root.after(1000, self.notify_after_delay)
                self.timer_running = True

    def on_moved(self, event):
        # Handle file movements (renaming or moving files/directories)
        src_path = event.src_path

        if self.ignore_file(src_path):
            return

        if src_path not in self.app.changed_files:
            self.app.changed_files.add(src_path)

            if not self.timer_running:
                # Schedule the notification after a delay
                self.timer_id = self.app.root.after(1000, self.notify_after_delay)
                self.timer_running = True

    
    def on_created(self, event):
        src_path = event.src_path

        if self.ignore_file(src_path):
            return

        # Check if it's the initial creation and not an opening
        if src_path not in self.app.changed_files and os.path.getsize(src_path) > 0:
            self.app.changed_files.add(src_path)

            if not self.timer_running:
                # Schedule the notification after a delay
                self.timer_id = self.app.root.after(1000, self.notify_after_delay)
                self.timer_running = True

class NotificationHandler(Thread):
    def __init__(self, app, notification_queue):
        super().__init__()
        self.app = app
        self.notification_queue = notification_queue
        self.daemon = True

    def run(self):
        while True:
            src_paths = self.notification_queue.get()
            self.app.show_notification(self.format_notification(src_paths))

    def format_notification(self, src_paths):
        app_title = "File Changed:" if len(src_paths) == 1 else "Files changed:"

        if len(src_paths) == 1:
            return app_title, f"\n{src_paths[0]}"
        else:
            return app_title, f"\n" + "\n".join(src_paths)

class FileWatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Luc's FileWatcher")
        self.watchers = []
        self.config_file = os.path.expanduser("~") + '/watcher_config.json'
        self.notification_queue = Queue()
        self.changed_files = set()

        self.notification_handler = NotificationHandler(self, self.notification_queue)
        self.notification_handler.start()

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ico.ico')
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        else:
            print("Icon file not found:", icon_path)

        self.create_gui()
        self.load_config()
        self.update_treeview()

    def create_gui(self):
        self.tree = ttk.Treeview(self.root, columns=('Status', 'Folder'))
        self.tree.heading('#0', text='Watcher')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Folder', text='Folder')

        self.tree.tag_configure('Active', foreground='green')
        self.tree.tag_configure('Inactive', foreground='red')

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
            watcher = {'folder': folder, 'status': 'Active'}
            self.watchers.append(watcher)
            self.update_treeview()
            self.save_config()
            self.start_observer(len(self.watchers) - 1)

    def start_watcher(self):
        selected_item = self.tree.selection()
        if selected_item:
            index = int(selected_item[0]) - 1
            self.watchers[index]['status'] = 'Active'
            self.start_observer(index)
            self.update_treeview()

    def stop_watcher(self):
        selected_item = self.tree.selection()
        if selected_item:
            index = int(selected_item[0]) - 1
            self.watchers[index]['status'] = 'Inactive'
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
            print("Observer is not available or already Inactive")

    def show_notification(self, notification_data):
        app_title, message = notification_data
        
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ico.ico')
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        else:
            print("Icon file not found:", icon_path)

        # Use plyer to display native notifications
        notification.notify(
            title=app_title,
            #message=message.replace('\n', ' '),  # Vervang nieuwe regels door spaties
            message=message,
            app_name='Luc\'s FileWatcher',
            app_icon=(icon_path),  # Voeg hier het volledige pad toe

        )

    def update_treeview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, watcher in enumerate(self.watchers, start=1):
            status = watcher['status']
            folder = watcher['folder']
            item_id = str(i)

            if status == 'Active':
                self.tree.insert('', 'end', iid=item_id, text=f"Watcher {i}", values=(status, folder), tags=('Active',))
            else:
                self.tree.insert('', 'end', iid=item_id, text=f"Watcher {i}", values=(status, folder), tags=('Inactive',))

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as file:
                    self.watchers = json.load(file)

                    for i, watcher in enumerate(self.watchers, start=1):
                        status = watcher.get('status', 'Inactive')
                        folder = watcher['folder']

                        if status == 'Active':
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
        if messagebox.askokcancel("Quit Luc's FileWatcher", "Do you really want to quit?\nYou will no longer receive notifications."):
            self.save_config()
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = FileWatcherApp(root)
    root.mainloop()
