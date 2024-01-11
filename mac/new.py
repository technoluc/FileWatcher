import os
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from queue import Queue
from threading import Thread
from plyer import notification  # Importeer de plyer-notificatiemodule

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
            self.app.show_notification(f"Bestand gewijzigd: {src_path}")

class FileWatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Luc's FileWatcher")

        self.watchers = []
        self.config_file = os.path.expanduser("~") + '/watcher_config.json'
        self.notification_queue = Queue()

        self.notification_handler = NotificationHandler(self, self.notification_queue)
        self.notification_handler.start()

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ico.ico')
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        else:
            print("Iconbestand niet gevonden:", icon_path)

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

        add_button = ttk.Button(self.root, text='Map toevoegen', command=self.add_watcher)
        start_button = ttk.Button(self.root, text='Watcher starten', command=self.start_watcher)
        stop_button = ttk.Button(self.root, text='Watcher stoppen', command=self.stop_watcher)
        remove_button = ttk.Button(self.root, text='Map verwijderen', command=self.remove_watcher)

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
            print("Observer is niet beschikbaar of al inactief")

    def show_notification(self, message):
        # Gebruik plyer om een notificatie naar het Mac-systeem te sturen
        notification.notify(
            title='Bestandswijziging',
            message=message,
            app_icon=None,
            timeout=5,
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
                print("Configuratiebestand bestaat niet.")
        except json.decoder.JSONDecodeError:
            print("Fout bij het decoderen van JSON.")
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

if __name__ == "__main__":
    root = tk.Tk()
    app = FileWatcherApp(root)
    root.mainloop()
