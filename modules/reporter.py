import os
import shutil
import cv2
import json
from datetime import datetime

class HTMLReporter:
    def __init__(self, reports_dir, logger=None):
        self.reports_dir = reports_dir
        self.logger = logger
        os.makedirs(self.reports_dir, exist_ok=True)
        self.steps = []
        self.annotations = []

    def draw_bounding_box(self, src_image_path, box, label, confidence, output_name):
        """Draws a green bounding box and confidence text on the image, saving it to the reports folder."""
        if not src_image_path or not os.path.exists(src_image_path):
            return None
        
        try:
            img = cv2.imread(src_image_path)
            if img is None:
                return None
                
            x, y, w, h = box
            # Draw green rectangle
            cv2.rectangle(img, (x, y), (x + w, y + h), (34, 197, 94), 3) # Green box (RGB 34, 197, 94 in BGR: 94, 197, 34)
            
            # Put label text
            text = f"{label} ({confidence:.2%})"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            
            # Get text size for background box
            (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
            
            # Draw solid background for text
            cv2.rectangle(img, (x, y - text_h - 10), (x + text_w + 10, y), (34, 197, 94), -1)
            # Draw text
            cv2.putText(img, text, (x + 5, y - 5), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
            
            dest_path = os.path.join(self.reports_dir, output_name)
            cv2.imwrite(dest_path, img)
            if self.logger:
                self.logger.debug(f"Saved annotated image to {dest_path}")
            return output_name
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to draw bounding box on image: {e}")
            return None

    def add_step(self, step_name, status, execution_time_ms=0, details="", image_path=None, annotated_image_name=None):
        copied_image_name = None
        if image_path and os.path.exists(image_path):
            try:
                # Copy image to reports folder to keep references local and self-contained
                base_name = os.path.basename(image_path)
                dest_path = os.path.join(self.reports_dir, base_name)
                shutil.copy(image_path, dest_path)
                copied_image_name = base_name
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to copy image to reports: {e}")
        
        self.steps.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "step_name": step_name,
            "status": status,
            "duration": execution_time_ms,
            "details": details,
            "image": copied_image_name,
            "annotated_image": annotated_image_name
        })

    def generate_report(self, device_id, total_duration_sec, overall_status, failure_reason=""):
        report_path = os.path.join(self.reports_dir, "report.html")
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        status_color = "#22c55e" if overall_status == "PASS" else "#ef4444"
        status_bg = "rgba(34, 197, 94, 0.15)" if overall_status == "PASS" else "rgba(239, 68, 68, 0.15)"
        
        # Build timeline HTML
        timeline_html = ""
        for i, step in enumerate(self.steps):
            step_status_color = "#22c55e" if step["status"] == "PASS" else "#ef4444" if step["status"] == "FAIL" else "#3b82f6"
            
            image_section = ""
            if step["image"]:
                img_src = step["image"]
                annotated_src = step["annotated_image"]
                
                if annotated_src:
                    image_section = f'''
                    <div class="image-container mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <span class="text-xs text-slate-400 block mb-1">Raw Screen Capture</span>
                            <img src="{img_src}" class="rounded-lg border border-slate-700 w-full object-contain cursor-pointer max-h-60" onclick="window.open('{img_src}')">
                        </div>
                        <div>
                            <span class="text-xs text-green-400 font-medium block mb-1">Detected Element Overlay</span>
                            <img src="{annotated_src}" class="rounded-lg border border-slate-700 w-full object-contain cursor-pointer max-h-60" onclick="window.open('{annotated_src}')">
                        </div>
                    </div>
                    '''
                else:
                    image_section = f'''
                    <div class="image-container mt-4">
                        <span class="text-xs text-slate-400 block mb-1">Screen Capture</span>
                        <img src="{img_src}" class="rounded-lg border border-slate-700 max-w-md object-contain cursor-pointer max-h-60" onclick="window.open('{img_src}')">
                    </div>
                    '''

            timeline_html += f'''
            <div class="timeline-item border-l-2 border-slate-700 pl-6 pb-8 relative last:pb-0">
                <!-- Status Dot -->
                <div class="absolute w-4 h-4 rounded-full -left-[9px] top-1" style="background-color: {step_status_color}; box-shadow: 0 0 10px {step_status_color}"></div>
                
                <div class="flex flex-wrap items-center justify-between gap-2">
                    <h3 class="text-lg font-semibold text-slate-200">{step["step_name"]}</h3>
                    <div class="flex items-center gap-2">
                        <span class="text-xs bg-slate-800 text-slate-400 px-2.5 py-1 rounded-md">{step["timestamp"]}</span>
                        <span class="text-xs px-2.5 py-1 rounded-md font-semibold" style="color: {step_status_color}; bg: rgba(0,0,0,0.1)">{step["status"]}</span>
                        {f'<span class="text-xs bg-slate-800 text-slate-300 px-2 py-1 rounded-md">{step["duration"]} ms</span>' if step["duration"] > 0 else ''}
                    </div>
                </div>
                <p class="text-sm text-slate-400 mt-2">{step["details"]}</p>
                {image_section}
            </div>
            '''

        # Generate complete HTML
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Logo Locator Tool - Automation Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: #0b0f19;
            color: #f8fafc;
        }}
        .glass {{
            background: rgba(17, 24, 39, 0.7);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
    </style>
</head>
<body class="p-6 md:p-12 min-h-screen">
    <div class="max-w-6xl mx-auto">
        <!-- Header -->
        <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
            <div>
                <h1 class="text-3xl font-bold tracking-tight bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-500 bg-clip-text text-transparent">
                    Logo Locator Automation Report
                </h1>
                <p class="text-slate-400 mt-1">Automated validation for Automotive Infotainment Displays</p>
            </div>
            <div class="flex items-center gap-3">
                <span class="text-sm text-slate-400">Report generated at: <span class="text-slate-200 font-medium">{timestamp_str}</span></span>
            </div>
        </header>

        <!-- Status Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <!-- Overall Status -->
            <div class="glass rounded-2xl p-6 flex flex-col justify-between">
                <span class="text-slate-400 text-sm font-medium">Overall Status</span>
                <div class="mt-4 flex items-center justify-between">
                    <span class="text-3xl font-bold" style="color: {status_color}">{overall_status}</span>
                    <span class="w-8 h-8 rounded-full flex items-center justify-center font-bold" style="background-color: {status_bg}; color: {status_color}">
                        { '✓' if overall_status == "PASS" else '✗' }
                    </span>
                </div>
            </div>
            <!-- Device ID -->
            <div class="glass rounded-2xl p-6 flex flex-col justify-between">
                <span class="text-slate-400 text-sm font-medium">Infotainment Device</span>
                <div class="mt-4">
                    <span class="text-2xl font-bold text-slate-100">{device_id.upper()}</span>
                    <span class="block text-xs text-blue-400 mt-1 font-semibold">ADB Connected</span>
                </div>
            </div>
            <!-- Duration -->
            <div class="glass rounded-2xl p-6 flex flex-col justify-between">
                <span class="text-slate-400 text-sm font-medium">Execution Time</span>
                <div class="mt-4">
                    <span class="text-3xl font-bold text-slate-100">{total_duration_sec:.2f}s</span>
                    <span class="block text-xs text-slate-400 mt-1">Total time elapsed</span>
                </div>
            </div>
            <!-- Steps Executed -->
            <div class="glass rounded-2xl p-6 flex flex-col justify-between">
                <span class="text-slate-400 text-sm font-medium">Steps Logged</span>
                <div class="mt-4">
                    <span class="text-3xl font-bold text-slate-100">{len(self.steps)}</span>
                    <span class="block text-xs text-slate-400 mt-1">Checks and interactions</span>
                </div>
            </div>
        </div>

        {f'''
        <!-- Failure Alert -->
        <div class="bg-red-500/10 border border-red-500/20 rounded-2xl p-6 mb-8 flex items-start gap-4">
            <span class="text-red-500 text-2xl font-bold leading-none">⚠</span>
            <div>
                <h4 class="text-red-400 font-semibold">Execution Failure Reason</h4>
                <p class="text-slate-300 text-sm mt-1">{failure_reason}</p>
            </div>
        </div>
        ''' if overall_status == "FAIL" else ""}

        <!-- Timeline -->
        <div class="glass rounded-3xl p-6 md:p-8">
            <h2 class="text-xl font-bold text-slate-100 mb-6">Execution Steps Timeline</h2>
            <div class="mt-4 flex flex-col">
                {timeline_html}
            </div>
        </div>
        
        <footer class="mt-12 text-center text-xs text-slate-500">
            Logo Locator Automation Tool &bull; Powered by Python, OpenCV & OCR
        </footer>
    </div>
</body>
</html>
'''
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        if self.logger:
            self.logger.info(f"HTML Report generated at {report_path}")
        return report_path
