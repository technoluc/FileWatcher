import os
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from queue import Queue
from threading import Thread


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, app, notification_queue):
        # Initialize the FileChangeHandler with the FileWatcherApp instance and notification queue
        self.app = app
        self.notification_queue = notification_queue
        self.changed_files = set()

    def on_modified(self, event):
        # Event handler for file modification events
        if event.is_directory:
            return

        src_path = event.src_path

        # Add a 1-second delay to consolidate notifications
        time.sleep(1)

        if src_path not in self.changed_files:
            self.changed_files.add(src_path)
            self.notification_queue.put(src_path)

class NotificationHandler(Thread):
    def __init__(self, app, notification_queue):
        # Initialize the NotificationHandler with the FileWatcherApp instance and notification queue
        super().__init__()
        self.app = app
        self.notification_queue = notification_queue
        self.daemon = True

    def run(self):
        # Run the thread to handle notifications
        while True:
            src_path = self.notification_queue.get()
            self.app.show_notification(f"File changed: {src_path}")

class FileWatcherApp:
    def __init__(self, root):
        # Initialize the FileWatcherApp with the root window
        self.root = root
        self.root.title("Luc's FileWatcher")

        # Initialize watchers list, configuration file path, and notification queue
        self.watchers = []
        self.config_file = os.path.expanduser("~") + '/watcher_config.json'  # Place the file in the home directory
        self.notification_queue = Queue()

        # Initialize and start the NotificationHandler thread
        self.notification_handler = NotificationHandler(self, self.notification_queue)
        self.notification_handler.start()
       
        # icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')
        # if os.path.exists(icon_path):
        #     root.iconbitmap(icon_path)
        # else:
        #     print("Icon file not found:", icon_path)

        # Create the GUI, load configuration, and update the treeview
        self.create_gui()
        self.load_config()
        self.update_treeview()

    def create_gui(self):
        # Create the graphical user interface components
        self.tree = ttk.Treeview(self.root, columns=('Status', 'Folder'))
        self.tree.heading('#0', text='Watcher')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Folder', text='Folder')

        # Define tags for the Treeview items
        self.tree.tag_configure('started', foreground='green')
        self.tree.tag_configure('stopped', foreground='red')

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
        # Add a folder watcher
        folder = filedialog.askdirectory()
        if folder:
            watcher = {'folder': folder, 'status': 'started'}
            self.watchers.append(watcher)
            self.update_treeview()  # Update the treeview after adding
            self.save_config()  # Save the configuration immediately after adding
            self.start_observer(len(self.watchers) - 1)  # Start the observer for the new watcher

    def start_watcher(self):
        # Start a selected watcher
        selected_item = self.tree.selection()
        if selected_item:
            index = int(selected_item[0]) - 1
            self.watchers[index]['status'] = 'started'
            self.start_observer(index)
            self.update_treeview()

    def stop_watcher(self):
        # Stop a selected watcher
        selected_item = self.tree.selection()
        if selected_item:
            index = int(selected_item[0]) - 1
            self.watchers[index]['status'] = 'stopped'
            self.stop_observer(index)
            self.update_treeview()

    def remove_watcher(self):
        # Remove a selected watcher
        selected_item = self.tree.selection()
        if selected_item:
            index = int(selected_item[0]) - 1
            del self.watchers[index]
            self.save_config()
            self.update_treeview()

    def start_observer(self, index):
        # Start the file system observer for a watcher
        folder = self.watchers[index]['folder']
        event_handler = FileChangeHandler(self, self.notification_queue)
        observer = Observer()
        observer.schedule(event_handler, folder, recursive=True)
        observer.start()
        self.watchers[index]['observer'] = observer

    def stop_observer(self, index):
        # Stop the file system observer for a watcher
        try:
            observer = self.watchers[index]['observer']
            observer.stop()
            observer.join()
        except KeyError:
            print("Observer is not available or already stopped")

    def show_notification(self, message):
        # Show a notification dialog
        messagebox.showinfo('File Change', message)

    def update_treeview(self):
        # Update the treeview with watcher information
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, watcher in enumerate(self.watchers, start=1):
            status = watcher['status']
            folder = watcher['folder']
            item_id = str(i)

            # Insert the item with the appropriate tag based on the status
            if status == 'started':
                self.tree.insert('', 'end', iid=item_id, text=f"Watcher {i}", values=(status, folder), tags=('started',))
            else:
                self.tree.insert('', 'end', iid=item_id, text=f"Watcher {i}", values=(status, folder), tags=('stopped',))

    def load_config(self):
        # Load configuration from a JSON file
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
        # Save configuration to a JSON file
        for watcher in self.watchers:
            if 'observer' in watcher:
                del watcher['observer']
        with open(self.config_file, 'w') as file:
            json.dump(self.watchers, file, indent=2)

    def on_close(self):
        # Save configuration before closing the application
        self.save_config()
        self.root.destroy()

if __name__ == "__main__":
    # Run the FileWatcherApp
    root = tk.Tk()
    app = FileWatcherApp(root)
    root.mainloop()
