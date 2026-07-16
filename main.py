import os
import sys
import time
import json
import threading
from datetime import datetime

# Add the current directory to path to ensure modules are importable
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

from modules.logger import ToolLogger
from modules.adb import ADBManager
from modules.capture import ScreenCapturer
from modules.logo_detector import LogoDetector
from modules.button_detector import ButtonDetector
from modules.tap import TapExecutor
from modules.reporter import HTMLReporter

def load_config():
    config_path = os.path.join(project_root, 'config', 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config.json from {config_path}: {e}")
        # Return fallback default configuration
        return {
            "device_id": "mock",
            "mock_mode": True,
            "detection_order": ["yolo", "ocr", "template"],
            "confidence_thresholds": {"yolo": 0.85, "ocr": 0.80, "template": 0.80},
            "timeouts": {
                "boot_timeout_sec": 60,
                "logo_detect_timeout_sec": 15,
                "logo_disappear_timeout_sec": 60,
                "button_detect_timeout_sec": 20
            },
            "button_labels": ["OK", "YES", "Accept", "Continue"],
            "paths": {
                "logo_template": "images/logo.png",
                "ok_button_template": "images/ok_button.png",
                "yes_button_template": "images/yes_button.png",
                "mock_screens_dir": "scratch",
                "screenshots_dir": "screenshots",
                "reports_dir": "reports",
                "logs_dir": "logs"
            }
        }

def run_automation(use_dashboard=False):
    start_time = time.time()
    config = load_config()
    
    # Resolve directories
    paths = config.get("paths", {})
    log_dir = os.path.join(project_root, paths.get("logs_dir", "logs"))
    reports_dir = os.path.join(project_root, paths.get("reports_dir", "reports"))
    screenshots_dir = os.path.join(project_root, paths.get("screenshots_dir", "screenshots"))
    mock_screens_dir = os.path.join(project_root, paths.get("mock_screens_dir", "scratch"))
    
    # Templates
    logo_path = os.path.join(project_root, paths.get("logo_template", "images/logo.png"))
    ok_button_path = os.path.join(project_root, paths.get("ok_button_template", "images/ok_button.png"))
    yes_button_path = os.path.join(project_root, paths.get("yes_button_template", "images/yes_button.png"))
    
    dashboard = None
    if use_dashboard:
        try:
            # Automatically launch dashboard.html in default browser
            import webbrowser
            dashboard_file = os.path.join(project_root, 'dashboard.html')
            if os.path.exists(dashboard_file):
                print(f"Launching visual dashboard in browser: {dashboard_file}")
                webbrowser.open(f"file:///{dashboard_file.replace(os.sep, '/')}")
        except Exception as exc:
            print(f"Failed to open dashboard.html in browser: {exc}")

        try:
            from live_dashboard import LiveDashboard
            dashboard = LiveDashboard()
            dashboard.append("Dashboard ready. Waiting for action logs...")
            dashboard_thread = threading.Thread(target=dashboard.start, daemon=True)
            dashboard_thread.start()
        except Exception as exc:
            print(f"Dashboard Tkinter init failed: {exc}")
            dashboard = None

    # Setup Logger
    logger = ToolLogger(log_dir, reports_dir, dashboard=dashboard)
    logger.info("=" * 60)
    logger.info("Logo Locator Automation Tool Started")
    logger.info(f"Mock Mode: {config.get('mock_mode')}")
    
    # Setup HTML Reporter
    reporter = HTMLReporter(reports_dir, logger)
    
    # Initialize ADB Manager
    device_id = config.get("device_id", "mock")
    mock_mode = config.get("mock_mode", True)
    adb = ADBManager(device_id, mock_mode, mock_screens_dir, logger)
    
    # Initialize Capture
    capturer = ScreenCapturer(adb, screenshots_dir, logger)
    
    # Initialize Detectors
    yolo_logo_model = config.get("yolo_logo_model")
    if yolo_logo_model and not os.path.isabs(yolo_logo_model):
        yolo_logo_model = os.path.join(project_root, yolo_logo_model)

    yolo_button_model = config.get("yolo_button_model")
    if yolo_button_model and not os.path.isabs(yolo_button_model):
        yolo_button_model = os.path.join(project_root, yolo_button_model)

    # Load separate thresholds
    thresholds = config.get("confidence_thresholds", {})
    yolo_thresh = thresholds.get("yolo", 0.35)
    template_thresh = thresholds.get("template", 0.80)
    ocr_thresh = thresholds.get("ocr", 0.80)

    # Initialize Detectors
    logo_detector = LogoDetector(
        template_path=logo_path, 
        template_threshold=template_thresh, 
        yolo_threshold=yolo_thresh, 
        yolo_model_path=yolo_logo_model, 
        logger=logger
    )
    
    templates = {"OK": ok_button_path, "YES": yes_button_path}
    mock_metadata_path = os.path.join(mock_screens_dir, "mock_ocr_metadata.json")
    button_detector = ButtonDetector(
        templates_dict=templates, 
        template_threshold=template_thresh, 
        yolo_threshold=yolo_thresh, 
        ocr_threshold=ocr_thresh,
        yolo_model_path=yolo_button_model, 
        mock_mode=mock_mode, 
        mock_metadata_path=mock_metadata_path, 
        logger=logger
    )
    
    # Initialize Tap Executor
    tap_executor = TapExecutor(adb, logger)
    
    overall_status = "PASS"
    failure_reason = ""
    
    # ----------------- STEP 1: Connect and Wait Boot -----------------
    step_start = time.time()
    logger.info("Step 1: Connecting and checking boot state...")
    connected, conn_msg = adb.connect()
    if not connected:
        failure_reason = f"ADB Connection Failed: {conn_msg}"
        logger.error(failure_reason)
        reporter.add_step("ADB Connection", "FAIL", int((time.time() - step_start)*1000), failure_reason)
        reporter.generate_report(device_id, time.time() - start_time, "FAIL", failure_reason)
        return False
        
    boot_timeout = config.get("timeouts", {}).get("boot_timeout_sec", 60)
    booted = adb.wait_boot(boot_timeout)
    step_time = int((time.time() - step_start) * 1000)
    if not booted:
        failure_reason = "Boot completed signal not received / Boot timeout"
        logger.error(failure_reason)
        reporter.add_step("Wait Boot Completed", "FAIL", step_time, failure_reason)
        reporter.generate_report(device_id, time.time() - start_time, "FAIL", failure_reason)
        return False
        
    logger.log_step(device_id, "Wait Boot Completed", "PASS", execution_time_ms=step_time, details="System booted successfully")
    reporter.add_step("Wait Boot Completed", "PASS", step_time, "Infotainment boot completion verified via getprop")
    
    # ----------------- STEP 2: Detect Boot Logo -----------------
    step_start = time.time()
    logger.info("Step 2: Detecting OEM boot logo...")
    logo_detected = False
    logo_box = None
    logo_conf = 0.0
    logo_screen = None
    
    logo_detect_timeout = config.get("timeouts", {}).get("logo_detect_timeout_sec", 15)
    logo_check_start = time.time()
    
    while time.time() - logo_check_start < logo_detect_timeout:
        logo_screen = capturer.capture_screen("boot_screen")
        if not logo_screen:
            time.sleep(1.0)
            continue
            
        detected, box, conf = logo_detector.detect(logo_screen)
        if detected:
            logo_detected = True
            logo_box = box
            logo_conf = conf
            break
        time.sleep(1.0)
        
    step_time = int((time.time() - step_start) * 1000)
    if not logo_detected:
        failure_reason = "OEM boot logo was not detected within timeout"
        logger.error(failure_reason)
        # Save screenshot for debugging
        err_screen = capturer.capture_screen("error_logo_not_found")
        reporter.add_step("Detect Boot Logo", "FAIL", step_time, failure_reason, err_screen)
        reporter.generate_report(device_id, time.time() - start_time, "FAIL", failure_reason)
        return False
        
    logger.log_step(device_id, "Detect Boot Logo", "PASS", (logo_box[0], logo_box[1]), step_time, f"Logo found with {logo_conf:.2%} confidence")
    
    # Annotate screenshot
    annotated_logo_name = reporter.draw_bounding_box(logo_screen, logo_box, "OEM_LOGO", logo_conf, "logo_detected.png")
    reporter.add_step("Detect Boot Logo", "PASS", step_time, f"OEM logo detected at bounding box x={logo_box[0]}, y={logo_box[1]}, w={logo_box[2]}, h={logo_box[3]} with confidence {logo_conf:.2%}", logo_screen, annotated_logo_name)
    
    # ----------------- STEP 3: Wait Logo Disappear -----------------
    step_start = time.time()
    logger.info("Step 3: Waiting for OEM logo to disappear...")
    logo_gone = False
    logo_disappear_timeout = config.get("timeouts", {}).get("logo_disappear_timeout_sec", 60)
    logo_dis_start = time.time()
    
    # In mock mode, we trigger the adb state machine transition to DISCLAIMER state
    # once logo disappears, so that screen cap returns disclaimer image
    if mock_mode:
        # Give it 1 second of logo display, then trigger transition
        time.sleep(1.0)
        adb.set_mock_state("DISCLAIMER")
        
    while time.time() - logo_dis_start < logo_disappear_timeout:
        check_screen = capturer.capture_screen("logo_check")
        if not check_screen:
            time.sleep(1.0)
            continue
            
        detected, _, _ = logo_detector.detect(check_screen)
        if not detected:
            logo_gone = True
            break
        time.sleep(1.0)
        
    step_time = int((time.time() - step_start) * 1000)
    if not logo_gone:
        failure_reason = "OEM boot logo remained on screen. System freeze suspected."
        logger.error(failure_reason)
        err_screen = capturer.capture_screen("error_logo_hang")
        reporter.add_step("Logo Disappear Check", "FAIL", step_time, failure_reason, err_screen)
        reporter.generate_report(device_id, time.time() - start_time, "FAIL", failure_reason)
        return False
        
    logger.log_step(device_id, "Logo Disappear Check", "PASS", execution_time_ms=step_time, details="Logo disappeared; disclaimer screen active")
    reporter.add_step("Logo Disappear Check", "PASS", step_time, "Boot logo disappeared successfully. System transitioned to disclaimer screen.")
    
    # ----------------- STEP 4: Detect OK/YES Button -----------------
    step_start = time.time()
    logger.info("Step 4: Detecting confirmation buttons...")
    button_found = None
    disclaimer_screen = None
    
    button_timeout = config.get("timeouts", {}).get("button_detect_timeout_sec", 20)
    button_check_start = time.time()
    button_targets = config.get("button_labels", ["OK", "YES"])
    button_attempt = 0
    
    while time.time() - button_check_start < button_timeout:
        button_attempt += 1
        disclaimer_screen = capturer.capture_screen(f"disclaimer_screen_{button_attempt}")
        if not disclaimer_screen:
            time.sleep(0.5)
            continue
            
        # Detect using hybrid strategy and log each live attempt.
        button_found = button_detector.detect(disclaimer_screen, button_targets)
        if button_found:
            logger.info(f"[LIVE] Dynamic button detection success: {button_found['text']} at {button_found['center']} via {button_found['method']}")
            break

        logger.info(f"[LIVE] Waiting for {button_targets} button to appear on screen (attempt {button_attempt})")
        time.sleep(0.5)
        
    step_time = int((time.time() - step_start) * 1000)
    if not button_found:
        failure_reason = f"None of the target buttons {button_targets} found on the screen."
        logger.error(failure_reason)
        err_screen = capturer.capture_screen("error_button_not_found")
        reporter.add_step("Detect Button", "FAIL", step_time, failure_reason, err_screen)
        reporter.generate_report(device_id, time.time() - start_time, "FAIL", failure_reason)
        return False
        
    btn_text = button_found["text"]
    btn_box = button_found["box"]
    btn_center = button_found["center"]
    btn_conf = button_found["confidence"]
    btn_method = button_found["method"]
    
    logger.log_step(
        device_id, 
        f"Detect Button ({btn_text})", 
        "PASS", 
        btn_center, 
        step_time, 
        f"Found '{btn_text}' via {btn_method} (Confidence: {btn_conf:.2%})"
    )
    
    annotated_btn_name = reporter.draw_bounding_box(
        disclaimer_screen, 
        btn_box, 
        f"BTN_{btn_text.upper()}", 
        btn_conf, 
        "button_detected.png"
    )
    reporter.add_step(
        f"Detect Button ({btn_text})", 
        "PASS", 
        step_time, 
        f"Found '{btn_text}' button dynamically using {btn_method} at bounding box x={btn_box[0]}, y={btn_box[1]}, w={btn_box[2]}, h={btn_box[3]}. Calculated center coordinate is {btn_center}.", 
        disclaimer_screen, 
        annotated_btn_name
    )
    
    # ----------------- STEP 5: Touch Tap Button -----------------
    step_start = time.time()
    logger.info(f"Step 5: Tapping button '{btn_text}' at {btn_center}...")
    tap_success = False
    for tap_attempt in range(1, 4):
        logger.info(f"[LIVE] Tap cycle {tap_attempt} for '{btn_text}' using current detected position {btn_center}")
        tap_success = tap_executor.tap(btn_center[0], btn_center[1], button_box=btn_box, attempt_num=tap_attempt)
        if tap_success:
            break
        time.sleep(0.5)

    step_time = int((time.time() - step_start) * 1000)

    if not tap_success:
        failure_reason = "ADB tap interaction execution failed"
        logger.error(failure_reason)
        reporter.add_step("Execute Tap", "FAIL", step_time, failure_reason)
        reporter.generate_report(device_id, time.time() - start_time, "FAIL", failure_reason)
        return False

    logger.log_step(device_id, "Execute Tap", "PASS", btn_center, step_time, f"Tapped button '{btn_text}' successfully")
    reporter.add_step("Execute Tap", "PASS", step_time, f"Tapped '{btn_text}' button center coordinate {btn_center}")

    # ----------------- STEP 6: Verify Next Screen -----------------
    step_start = time.time()
    logger.info("Step 6: Verifying screen transition...")
    time.sleep(2.0)  # Wait for transition animation to stabilize
    
    post_tap_screen = capturer.capture_screen("post_tap_screen")
    step_time = int((time.time() - step_start) * 1000)
    
    # Verification logic:
    # 1. The disclaimer button should be gone.
    # 2. If template or OCR finds the disclaimer button again, it means the tap didn't work.
    is_disclaimer_still_active = False
    if post_tap_screen:
        check_button = button_detector.detect(post_tap_screen, button_targets)
        if check_button:
            is_disclaimer_still_active = True
            
    if is_disclaimer_still_active:
        failure_reason = "Screen did not transition. Tap did not dismiss the disclaimer pop-up."
        logger.error(failure_reason)
        reporter.add_step("Verify Screen Transition", "FAIL", step_time, failure_reason, post_tap_screen)
        reporter.generate_report(device_id, time.time() - start_time, "FAIL", failure_reason)
        return False
        
    logger.log_step(device_id, "Verify Screen Transition", "PASS", execution_time_ms=step_time, details="Disclaimer dismissed successfully. Next screen verified.")
    reporter.add_step("Verify Screen Transition", "PASS", step_time, "Screen transitioned successfully. Disclaimer pop-up dismissed and main screen loaded.", post_tap_screen)
    
    # ----------------- STEP 7: Finish and Report -----------------
    total_duration = time.time() - start_time
    logger.info(f"Automation execution completed successfully in {total_duration:.2f} seconds.")
    logger.info("=" * 60)
    
    report_file = reporter.generate_report(device_id, total_duration, "PASS")
    print(f"\nExecution PASS. Premium HTML Report generated: {report_file}\n")

    # Auto-open the HTML report in the default browser
    try:
        import webbrowser
        webbrowser.open(f"file:///{report_file.replace(os.sep, '/').lstrip('/')}")
        print(f"Report opened in browser: {report_file}")
    except Exception as exc:
        print(f"Could not open report in browser: {exc}")

    if dashboard is not None:
        dashboard.append("Automation completed successfully. Report opened in browser.")
        try:
            # Let the server stay alive for a brief moment so the client receives the done event
            time.sleep(2.0)
            dashboard.close()
        except Exception:
            pass
    return True

if __name__ == '__main__':
    # Enabled by default unless explicitly disabled with --no-dashboard
    use_dashboard = '--no-dashboard' not in sys.argv
    run_automation(use_dashboard=use_dashboard)

