import subprocess

def send_notification(title, subtitle, body):
    # Path to the Swift executable
    executable_path = '/Users/luckurstjens/Projects/FileWatcher/mac/v15/NotificationSender'

    # Call the Swift program with the notification parameters
    subprocess.run([executable_path, title, subtitle, body])

# Example usage
send_notification("Test Title", "Test Subtitle", "This is a test message.")
