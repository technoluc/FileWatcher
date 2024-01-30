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

# Notificatons per event
# Multiple per event but perfect base for Python --> Swift

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

        file_events = list(self.app.changed_files)
        self.notification_queue.put(file_events)
        self.app.changed_files.clear()
        self.timer_running = False

    def ignore_file(self, file_path):
        ignored_files = ['.DS_Store', 'Thumbs.db']
        basename = os.path.basename(file_path)

        # Check if the file is hidden
        if basename.startswith('.') or basename.startswith('~$'):
            return True
        return basename in ignored_files

    def on_modified(self, event):
        if event.is_directory or self.ignore_file(event.src_path):
            return

        event_type = 'edited'
        if os.path.getmtime(event.src_path) == os.path.getctime(event.src_path):
            event_type = 'created'

        file_event = {'type': event_type, 'path': event.src_path}
        self.app.changed_files.add(json.dumps(file_event))

        if not self.timer_running:
            self.timer_id = self.app.root.after(1000, self.notify_after_delay)
            self.timer_running = True

    def on_moved(self, event):
        if self.ignore_file(event.src_path):
            return

        file_event = {'type': 'moved', 'src_path': event.src_path, 'dest_path': event.dest_path}
        self.app.changed_files.add(json.dumps(file_event))

        if not self.timer_running:
            self.timer_id = self.app.root.after(1000, self.notify_after_delay)
            self.timer_running = True

    def on_created(self, event):
        if event.is_directory or self.ignore_file(event.src_path):
            return

        file_event = {'type': 'created', 'path': event.src_path}
        self.app.changed_files.add(json.dumps(file_event))

        if not self.timer_running:
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
            file_events = self.notification_queue.get()
            for file_event_json in file_events:
                file_event = json.loads(file_event_json)
                notification_title, notification_message = self.format_notification(file_event)
                self.app.show_notification(notification_title, notification_message)

    def format_notification(self, file_event):
        event_type = file_event['type']
        if event_type == 'moved':
            return (
                f"File Moved: {os.path.basename(file_event['src_path'])}",
                f"{file_event['src_path']} was moved to {file_event['dest_path']}"
            )
        elif event_type == 'created':
            return (
                f"File Created: {os.path.basename(file_event['path'])}",
                f"{file_event['path']} was created."
            )
        elif event_type == 'edited':
            return (
                f"File Edited: {os.path.basename(file_event['path'])}",
                f"{file_event['path']} was edited."
            )


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

    def show_notification(self, title, message):
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ico.ico')
        if not os.path.exists(icon_path):
            print("Icon file not found:", icon_path)
            return

        # Use plyer to display native notifications
        notification.notify(
            title=title,
            message=message,
            app_name="Luc's FileWatcher",
            app_icon=icon_path
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
