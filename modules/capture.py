import os
from datetime import datetime
import shutil

class ScreenCapturer:
    def __init__(self, adb_manager, screenshots_dir, logger=None):
        self.adb = adb_manager
        self.screenshots_dir = screenshots_dir
        self.logger = logger
        os.makedirs(self.screenshots_dir, exist_ok=True)

    def capture_screen(self, label="screen"):
        """Captures the device screen, saves a timestamped copy, and returns the path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{label}_{timestamp}.png"
        archive_path = os.path.join(self.screenshots_dir, filename)
        
        # Capture screen from ADB
        success = self.adb.capture(archive_path)
        if success:
            if self.logger:
                self.logger.debug(f"Captured screen and saved to: {archive_path}")
            return archive_path
        else:
            if self.logger:
                self.logger.error("Failed to capture screen.")
            return None
