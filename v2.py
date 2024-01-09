import os
import json
import tkinter as tk
from tkinter import filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from tkinter import messagebox

CONFIG_FILE_PATH = os.path.join(os.path.expanduser("~"), "watcher_config.json")

class Watcher:
    def __init__(self, root, watcher_listbox):
        self.root = root
        self.watcher_listbox = watcher_listbox
        self.watchers = self.load_watchers_from_config()

    def create_watcher(self):
        folder_path = filedialog.askdirectory(title="Selecteer map")
        if folder_path:
            try:
                watcher = FileSystemEventHandler()
                watcher.folder_path = folder_path
                watcher.on_modified = self.on_modified
                watcher.on_created = self.on_created
                observer = Observer()
                observer.schedule(watcher, folder_path, recursive=True)
                self.watchers.append({"folder_path": folder_path, "watcher": watcher, "observer": observer, "active": False})
                self.update_gui()
                self.save_watchers_to_config()
            except Exception as e:
                messagebox.showerror("Fout", f"Fout bij het maken van de watcher: {e}")

    def on_modified(self, event):
        self.show_popup("Let op!", f"Bestand gewijzigd: {event.src_path}")

    def on_created(self, event):
        self.show_popup("Let op!", f"Nieuw bestand aangemaakt: {event.src_path}")

    def show_popup(self, title, message):
        response = messagebox.showinfo(title, message)
        if response == "ok":
            pass

    # def start_watchers(self):
    #     selected_index = self.watcher_listbox.curselection()
    #     if selected_index:
    #         selected_index = int(selected_index[0])
    #         watcher_data = self.watchers[selected_index]
    #         if not watcher_data["active"]:
    #             observer = watcher_data["observer"]
    #             observer.start()
    #             watcher_data["active"] = True
    #             self.update_gui()

    def start_watchers(self):
        selected_index = self.watcher_listbox.curselection()
        if selected_index:
            selected_index = int(selected_index[0])
            watcher_data = self.watchers[selected_index]
            if not watcher_data["active"]:
                observer = watcher_data["observer"]
                observer.start()
                watcher_data["active"] = True
                self.update_gui()
            else:
                messagebox.showinfo("Info", "Watcher is already active.")


    def stop_watchers(self):
        selected_index = self.watcher_listbox.curselection()
        if selected_index:
            selected_index = int(selected_index[0])
            watcher_data = self.watchers[selected_index]
            observer = watcher_data["observer"]
            
            if watcher_data["active"]:
                observer.stop()
                watcher_data["active"] = False
                self.update_gui()

                if observer.is_alive():
                    observer.join(timeout=1)  # Wait for the thread to finish with a timeout

            else:
                messagebox.showinfo("Info", "Watcher is not active.")

    def remove_watcher(self):
        selected_index = self.watcher_listbox.curselection()
        if selected_index:
            selected_index = int(selected_index[0])
            watcher_data = self.watchers[selected_index]
            if watcher_data["active"]:
                observer = watcher_data["observer"]
                observer.stop()
                observer.join(timeout=1)  # Wait for the thread to finish with a timeout
            self.watcher_listbox.delete(selected_index)
            del self.watchers[selected_index]
            self.update_gui()
            self.save_watchers_to_config()

    def save_watchers_to_config(self):
        watchers_data = [{"folder_path": watcher_data["folder_path"], "active": watcher_data["active"]} for watcher_data in self.watchers]
        with open(CONFIG_FILE_PATH, "w") as config_file:
            json.dump(watchers_data, config_file)

    def load_watchers_from_config(self):
        loaded_watchers = []
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, "r") as config_file:
                try:
                    config_data = json.load(config_file)
                    for watcher_data in config_data:
                        folder_path = watcher_data.get("folder_path", "")
                        active = watcher_data.get("active", False)
                        watcher = FileSystemEventHandler()
                        watcher.folder_path = folder_path
                        watcher.on_modified = self.on_modified
                        watcher.on_created = self.on_created
                        observer = Observer()
                        observer.schedule(watcher, folder_path, recursive=True)
                        loaded_watchers.append({"folder_path": folder_path, "watcher": watcher, "observer": observer, "active": active})
                except json.decoder.JSONDecodeError as e:
                    print(f"Error loading configuration: {e}")

        self.watchers = loaded_watchers
        self.update_gui()
        return loaded_watchers

    def update_gui(self):
        self.watcher_listbox.delete(0, tk.END)
        for watcher_data in self.watchers:
            status = "Actief" if watcher_data["active"] else "Inactief"
            display_text = f"{watcher_data['folder_path']} - {status}"
            self.watcher_listbox.insert(tk.END, display_text)

#def on_closing():
#    watcher_manager.stop_watchers()
#    watcher_manager.save_watchers_to_config()
#    root.destroy()

# def on_closing():
#     if any(watcher["active"] for watcher in watcher_manager.watchers):
#         watcher_manager.stop_watchers()
#         watcher_manager.save_watchers_to_config()
#     root.destroy()
    
    
def on_closing():
    for watcher_data in watcher_manager.watchers:
        observer = watcher_data["observer"]
        if observer.is_alive():
            watcher_data["active"] = True
        else:
            watcher_data["active"] = False

    watcher_manager.stop_watchers()
    watcher_manager.save_watchers_to_config()
    root.destroy()


def main():
    global root
    root = tk.Tk()
    root.title("Watcher App")

    default_width = root.winfo_reqwidth() * 2
    default_height = root.winfo_reqheight() * 2
    root.geometry(f"{default_width}x{default_height}")

    watcher_listbox = tk.Listbox(root)
    watcher_listbox.pack(padx=10, pady=10)

    global watcher_manager
    watcher_manager = Watcher(root, watcher_listbox)

    create_button = tk.Button(root, text="Maak Watcher", command=watcher_manager.create_watcher)
    create_button.pack(pady=10)

    start_button = tk.Button(root, text="Start Watcher", command=watcher_manager.start_watchers)
    start_button.pack(pady=10)

    stop_button = tk.Button(root, text="Stop Watcher", command=watcher_manager.stop_watchers)
    stop_button.pack(pady=10)

    remove_button = tk.Button(root, text="Verwijder Watcher", command=watcher_manager.remove_watcher)
    remove_button.pack(pady=10)

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
