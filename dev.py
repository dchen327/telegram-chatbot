"""
Development script with auto-reload functionality.
Watches for file changes and restarts the bot automatically.
"""
import subprocess
import sys
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class BotReloadHandler(FileSystemEventHandler):
    """Handler that restarts the bot when Python files change."""
    
    def __init__(self):
        self.process = None
        self.start_bot()
    
    def start_bot(self):
        """Start the bot process."""
        if self.process:
            print("\n🛑 Stopping bot...")
            self.process.terminate()
            self.process.wait()
        
        print("🚀 Starting bot...")
        self.process = subprocess.Popen(
            [sys.executable, "bot.py"],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        # Only reload on Python file changes
        if event.src_path.endswith('.py'):
            print(f"\n📝 Detected change in {event.src_path}")
            time.sleep(0.5)  # Wait a bit to avoid multiple triggers
            self.start_bot()


def main():
    """Main function to start the file watcher."""
    event_handler = BotReloadHandler()
    observer = Observer()
    
    # Watch the current directory for changes
    watch_path = Path(__file__).parent
    observer.schedule(event_handler, str(watch_path), recursive=False)
    
    observer.start()
    print(f"👀 Watching {watch_path} for changes...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping watcher and bot...")
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
            event_handler.process.wait()
    
    observer.join()


if __name__ == "__main__":
    main()

