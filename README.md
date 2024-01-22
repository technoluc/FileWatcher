# Luc's FileWatcher

Luc's FileWatcher is a Python application that monitors specified folders for file changes and provides notifications.

## Features

- Single Pop-up notification for file changes.
- Better formatting of notifications.
- Notifications for folder movements.
- Ignores Thumbs.db and .DS_Store files.
- Ask to Quit functionality.
- Scaling for better user experience.

## Dependencies

Make sure to install the required dependencies using:

```bash
pip install Pillow watchdog plyer pyinstaller
```


## How to Use

1. Run the script using Python:

```bash
python FileWatcher_v9_win.py
```

2. To package the application, use PyInstaller with the following command:

```powershell
& "pyinstaller.exe" `
--onefile `
--windowed `
--icon ico.ico `
--hidden-import plyer.platforms.win.notification `
--hidden-import plyer `
--add-binary "ico.ico;." `
--add-data "$(python -c 'import plyer; print(plyer.__path__[0])'):." `
.\FileWatcher_v9_win.py
```

Make sure to run this command in the directory where your `FileWatcher_v9_win.py` script is located.

## Configuration

The application stores the configuration in a JSON file (`watcher_config.json`). You can modify this file directly or use the GUI.

## Contributing

Feel free to contribute to the development of Luc's FileWatcher by submitting issues or pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
```

Feel free to customize the content further if needed. Let me know if there's anything else I can help you with!

``````