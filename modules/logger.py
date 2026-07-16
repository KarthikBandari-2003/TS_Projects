import os
import logging
import csv
from datetime import datetime

class ToolLogger:
    def __init__(self, log_dir, reports_dir, dashboard=None):
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(reports_dir, exist_ok=True)
        
        self.log_file = os.path.join(log_dir, 'logo_locator.log')
        self.csv_file = os.path.join(reports_dir, 'execution_log.csv')
        self.dashboard = dashboard
        
        # Configure root/module logger
        self.logger = logging.getLogger("LogoLocator")
        self.logger.setLevel(logging.DEBUG)
        self._handlers = []
        
        # Avoid duplicating handlers if already initialized
        if not self.logger.handlers:
            # File handler
            fh = logging.FileHandler(self.log_file, encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            self._handlers.append(fh)
            
            # Console handler
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            self._handlers.append(ch)
            
            # Formatter
            formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

        # Initialize CSV file if not exists
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Device", "Step", "Status", "Coordinates", "ExecutionTimeMs", "Details"])

    def _emit_to_dashboard(self, level, msg):
        if self.dashboard is not None:
            try:
                self.dashboard.append(msg, level=level)
            except Exception:
                pass

    def info(self, msg):
        self.logger.info(msg)
        self._emit_to_dashboard("INFO", msg)

    def debug(self, msg):
        self.logger.debug(msg)
        self._emit_to_dashboard("DEBUG", msg)

    def warn(self, msg):
        self.logger.warning(msg)
        self._emit_to_dashboard("WARNING", msg)

    def error(self, msg):
        self.logger.error(msg)
        self._emit_to_dashboard("ERROR", msg)

    def close(self):
        for handler in list(getattr(self.logger, "handlers", [])):
            try:
                handler.flush()
                handler.close()
            except Exception:
                pass
            try:
                self.logger.removeHandler(handler)
            except Exception:
                pass

    def log_step(self, device, step_name, status, coordinates=None, execution_time_ms=0, details=""):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        coord_str = f"({coordinates[0]},{coordinates[1]})" if coordinates else "N/A"
        
        # Log to logger file
        self.info(f"Step: {step_name} | Status: {status} | Coord: {coord_str} | Time: {execution_time_ms}ms | {details}")
        
        # Log to CSV
        try:
            with open(self.csv_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, device, step_name, status, coord_str, execution_time_ms, details])
        except Exception as e:
            self.logger.error(f"Failed to write to CSV log: {e}")
