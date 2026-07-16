import os
import subprocess
import shutil
import time

class ADBManager:
    def __init__(self, device_id="mock", mock_mode=True, mock_dir=None, logger=None):
        self.device_id = device_id
        self.mock_mode = mock_mode
        self.mock_dir = mock_dir
        self.logger = logger
        
        # State machine for mock simulation: 'OFFLINE' -> 'BOOTING' -> 'LOGO_SHOWN' -> 'DISCLAIMER' -> 'HOME'
        self.mock_state = 'OFFLINE'
        self.mock_capture_count = 0
        
        if self.mock_mode:
            if self.logger:
                self.logger.info("ADB Manager initialized in MOCK SIMULATION mode.")
            self.mock_state = 'BOOTING'

    def connect(self):
        if self.mock_mode:
            time.sleep(0.5)
            if self.logger:
                self.logger.info("Mock ADB: Connected to virtual device.")
            return True, "Mock device connected successfully"
        
        cmd = ["adb", "connect", self.device_id]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if res.returncode == 0:
                if self.logger:
                    self.logger.info(f"Connected to ADB device: {self.device_id}")
                return True, res.stdout
            else:
                return False, res.stderr
        except Exception as e:
            return False, str(e)

    def execute(self, shell_cmd):
        if self.mock_mode:
            # Simulate boot completed checks
            if "getprop sys.boot_completed" in shell_cmd:
                if self.mock_state == 'BOOTING':
                    # Simulate it's still booting up
                    self.mock_capture_count += 1
                    if self.mock_capture_count >= 2:
                        self.mock_state = 'LOGO_SHOWN'
                        if self.logger:
                            self.logger.debug("Mock state transitioned to LOGO_SHOWN")
                        return "1"  # Android is booted, and logo shows
                    return "0"
                else:
                    return "1"
            return ""

        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(["shell", shell_cmd])
        
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            return res.stdout.strip()
        except Exception as e:
            if self.logger:
                self.logger.error(f"ADB execution failed: {e}")
            return ""

    def tap(self, x, y):
        if self.mock_mode:
            if self.logger:
                self.logger.info(f"Mock ADB: Executed touch tap at ({x}, {y})")
            
            # OK button center is ~ (910, 545). YES button center is ~ (410, 545)
            # Let's check if the tap lands in the OK button bounding box: [850, 520, 970, 570]
            # or YES button bounding box: [350, 520, 470, 570]
            if self.mock_state == 'DISCLAIMER':
                if 850 <= x <= 970 and 520 <= y <= 570:
                    self.mock_state = 'HOME'
                    if self.logger:
                        self.logger.info("Mock state transitioned to HOME (OK button pressed successfully)")
                    return True
                elif 350 <= x <= 470 and 520 <= y <= 570:
                    self.mock_state = 'HOME'
                    if self.logger:
                        self.logger.info("Mock state transitioned to HOME (YES button pressed successfully)")
                    return True
                else:
                    if self.logger:
                        self.logger.warn(f"Mock ADB: Tap at ({x}, {y}) missed the disclaimer buttons!")
                    return False
            return False

        shell_cmd = f"input tap {x} {y}"
        res = self.execute(shell_cmd)
        return True

    def reboot(self):
        if self.mock_mode:
            self.mock_state = 'BOOTING'
            self.mock_capture_count = 0
            if self.logger:
                self.logger.info("Mock ADB: Device reboot initiated.")
            return True
        
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.append("reboot")
        try:
            subprocess.run(cmd, timeout=10)
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to reboot: {e}")
            return False

    def capture(self, output_path):
        if self.mock_mode:
            # Copy different mock screens depending on state
            src_file = 'mock_boot_1.png'
            if self.mock_state == 'BOOTING':
                src_file = 'mock_boot_1.png'
            elif self.mock_state == 'LOGO_SHOWN':
                src_file = 'mock_boot_2.png'
            elif self.mock_state == 'DISCLAIMER':
                src_file = 'mock_disclaimer.png'
            elif self.mock_state == 'HOME':
                src_file = 'mock_home.png'
            
            src_path = os.path.join(self.mock_dir, src_file)
            if os.path.exists(src_path):
                shutil.copy(src_path, output_path)
                if self.logger:
                    self.logger.debug(f"Mock Capture: Copied {src_file} to {output_path} (State: {self.mock_state})")
                return True
            else:
                if self.logger:
                    self.logger.error(f"Mock screen source file does not exist: {src_path}")
                return False

        # Physical ADB Screen Capture
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        # Use exec-out screencap for binary speed redirection
        cmd.extend(["exec-out", "screencap", "-p"])
        
        try:
            with open(output_path, "wb") as f:
                res = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=15)
                if res.returncode == 0:
                    return True
                else:
                    if self.logger:
                        self.logger.error(f"ADB screencap failed: {res.stderr.decode()}")
                    return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"ADB capture exception: {e}")
            return False

    def wait_boot(self, timeout_sec=60):
        if self.logger:
            self.logger.info("Waiting for boot completion...")
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            res = self.execute("getprop sys.boot_completed")
            if res == "1":
                if self.logger:
                    self.logger.info("Boot completed!")
                return True
            time.sleep(1.0)
        
        if self.logger:
            self.logger.error("Boot timeout exceeded.")
        return False

    def set_mock_state(self, state):
        """Helper to manually drive mock state transitions from test scripts"""
        if self.mock_mode:
            self.mock_state = state
            if self.logger:
                self.logger.debug(f"Mock state explicitly set to: {state}")
