import time

class TapExecutor:
    def __init__(self, adb_manager, logger=None):
        self.adb = adb_manager
        self.logger = logger

    def tap(self, x, y, button_box=None, attempt_num=1):
        """Sends tap command through ADB and returns success status."""
        if x < 0 or y < 0:
            if self.logger:
                self.logger.error(f"Invalid negative coordinates: ({x}, {y})")
            return False

        candidates = [(x, y)]
        if button_box:
            x0, y0, w, h = button_box
            candidates.extend([
                (x0 + max(10, w // 4), y0 + h // 2),
                (x0 + min(w - 10, 3 * w // 4), y0 + h // 2),
                (x0 + w // 2, y0 + max(10, h // 4)),
                (x0 + w // 2, y0 + min(h - 10, 3 * h // 4)),
            ])

        for idx, candidate in enumerate(candidates, start=1):
            cx, cy = candidate
            if self.logger:
                self.logger.info(f"[LIVE] Tap attempt {attempt_num} candidate {idx}/{len(candidates)} at ({cx}, {cy})")

            success = self.adb.tap(cx, cy)
            if success:
                if self.logger:
                    self.logger.info(f"[LIVE] Tap succeeded at ({cx}, {cy})")
                return True

        if self.logger:
            self.logger.error(f"Tap command execution failed for all candidates around ({x}, {y}).")
        return False
