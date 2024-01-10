import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

CONFIG_FILE_PATH = os.path.join(os.path.expanduser("~"), "watcher_config.json")

class WatcherEventHandler(FileSystemEventHandler):
    def __init__(self, app, path):
        super().__init__()
        self.app = app
        self.path = path

    def on_modified(self, event):
        if event.is_directory:
            return
        changed_file = os.path.relpath(event.src_path, self.path)
        self.app.show_notification(f"Map {self.path} is gewijzigd!\nBestand: {changed_file}", self.path)
        # self.app.show_popup(f"Map {self.path} is gewijzigd!\nBestand: {changed_file}", self.path)

class WatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Luc's Watcher App")

        self.watchers = []
        self.tree = None  # Add this line to initialize 'tree'
        self.create_gui()
        self.load_watchers_from_config()

    def create_gui(self):
        style = ttk.Style()
        style.configure("TButton", padding=(5, 5, 5, 5), width=20)

        tree_columns = ("Path", "Status")
        self.tree = ttk.Treeview(self.root, columns=tree_columns, show="headings", selectmode="browse")
        for col in tree_columns:
            self.tree.heading(col, text=col)
        self.tree.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        btn_frame = ttk.Frame(self.root)
        btn_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        add_btn = ttk.Button(btn_frame, text="Voeg map toe", command=self.create_watcher)
        start_btn = ttk.Button(btn_frame, text="Start Watchers", command=self.start_watchers)
        stop_btn = ttk.Button(btn_frame, text="Stop Watchers", command=self.stop_watchers)
        remove_btn = ttk.Button(btn_frame, text="Verwijder Watcher", command=self.remove_watcher)

        add_btn.grid(row=0, column=0, padx=5)
        start_btn.grid(row=0, column=1, padx=5)
        stop_btn.grid(row=0, column=2, padx=5)
        remove_btn.grid(row=0, column=3, padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_watcher(self):
        folder_path = filedialog.askdirectory(title="Selecteer een map om te watchen")
        if folder_path and folder_path not in [watcher["folder_path"] for watcher in self.watchers]:
            self.watchers.append({"folder_path": folder_path, "watcher": None, "observer": None})
            self.update_tree()

    def start_watchers(self):
        for watcher_data in self.watchers:
            path = watcher_data["folder_path"]
            event_handler = WatcherEventHandler(self, path)
            observer = Observer()
            observer.schedule(event_handler, path, recursive=True)
            observer.start()
            self.watchers[self.watchers.index(watcher_data)]["observer"] = observer
        self.update_tree()

    def stop_watchers(self):
        for watcher_data in self.watchers:
            observer = watcher_data["observer"]
            if observer:
                observer.stop()
                observer.join()
        self.update_tree()

    def remove_watcher(self):
        selected_item = self.tree.selection()
        if selected_item:
            index = int(selected_item[0][1:]) - 1
            watcher_data = self.watchers[index]
            observer = watcher_data.get("observer")
            if observer:
                observer.stop()
                observer.join()
            del self.watchers[index]
            self.update_tree()

    # def show_notification(self, message, path):
    #     result = messagebox.askquestion("Map gewijzigd", message, icon='info', buttons=['Sluiten', 'Open map'])
    #     if result == 'Open map':
    #         self.open_folder(path)
    
    def show_notification(self, message, path):
        try:
            result = messagebox.askquestion("Map gewijzigd", message, icon='info', type=messagebox.YESNO)
            if result == messagebox.YES:
                self.open_folder(path)
        except Exception as e:
            messagebox.showerror("Fout bij melding", f"Fout bij weergeven melding: {e}")

    # def on_modified(self, event):
    #     self.show_popup("Let op!", f"Bestand gewijzigd: {event.src_path}")

    # def show_popup(self, title, message):
    #     response = messagebox.showinfo(title, message)
    #     if response == "ok":
    #         pass

    def open_folder(self, path):
        os.startfile(path)

    def update_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, watcher_data in enumerate(self.watchers):
            observer = watcher_data.get("observer")
            status = "Actief" if observer and observer.is_alive() else "Inactief"
            self.tree.insert("", "end", values=(watcher_data["folder_path"], status))

    def load_watchers_from_config(self):
        loaded_watchers = []
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, "r") as config_file:
                try:
                    config_data = json.load(config_file)
                    for watcher_data in config_data:
                        folder_path = watcher_data.get("folder_path", "")
                        loaded_watchers.append({"folder_path": folder_path, "watcher": None, "observer": None})
                except json.decoder.JSONDecodeError as e:
                    print(f"Error loading configuration: {e}")
        self.watchers = loaded_watchers
        self.update_tree()
        return loaded_watchers

    def save_watchers_to_config(self):
        watchers_data = [{"folder_path": watcher_data["folder_path"]} for watcher_data in self.watchers]
        with open(CONFIG_FILE_PATH, "w") as config_file:
            json.dump(watchers_data, config_file)

    def on_closing(self):
        self.stop_watchers()
        self.save_watchers_to_config()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = WatcherApp(root)
    root.mainloop()
