import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_modified(self, event):
        if event.is_directory:
            return
        self.app.show_notification(f"Bestand gewijzigd: {event.src_path}")

class FileWatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Luc's File Watcher App")

        self.watchers = []
        self.load_config()

        self.create_gui()

    def create_gui(self):
        self.tree = ttk.Treeview(self.root, columns=('Status', 'Map'))
        self.tree.heading('#0', text='Watcher')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Map', text='Map')

        add_button = ttk.Button(self.root, text='Map Toevoegen', command=self.add_watcher)
        start_button = ttk.Button(self.root, text='Watcher Starten', command=self.start_watcher)
        stop_button = ttk.Button(self.root, text='Watcher Stoppen', command=self.stop_watcher)
        remove_button = ttk.Button(self.root, text='Map Verwijderen', command=self.remove_watcher)

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
            self.update_treeview()  # Update de treeview na toevoegen

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
            self.update_treeview()

    def start_observer(self, index):
        folder = self.watchers[index]['folder']
        event_handler = FileChangeHandler(self)
        observer = Observer()
        observer.schedule(event_handler, folder, recursive=True)
        observer.start()
        self.watchers[index]['observer'] = observer

    def stop_observer(self, index):
        observer = self.watchers[index]['observer']
        observer.stop()
        observer.join()

    def show_notification(self, message):
        messagebox.showinfo('Bestandswijziging', message)

    def update_treeview(self):
        # Wissen van de bestaande items in de treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Toevoegen van de watchers aan de treeview
        for i, watcher in enumerate(self.watchers, start=1):
            status = watcher['status']
            folder = watcher['folder']
            self.tree.insert('', 'end', iid=str(i), text=f"Watcher {i}", values=(status, folder))

    def load_config(self):
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as file:
                    self.watchers = json.load(file)
        except json.decoder.JSONDecodeError:
            self.watchers = []

    def save_config(self):
        for watcher in self.watchers:
            if 'observer' in watcher:
                del watcher['observer']
        with open('config.json', 'w') as file:
            json.dump(self.watchers, file, indent=2)

    def on_close(self):
        self.save_config()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = FileWatcherApp(root)
    root.mainloop()
