"""
Optimized YOLOv8 live detection stream for Raspberry Pi 5.

Colour pipeline (fixed):
  picamera2 → RGB888 array
  → cv2.cvtColor(RGB→BGR)   [YOLO + OpenCV draw expect BGR]
  → cv2.imencode(".jpg")     [OpenCV encodes BGR correctly as JPEG]
  → browser renders JPEG     [correct colours, no swap needed]
"""

import threading
import time
import cv2
import numpy as np
from flask import Flask, Response, render_template_string, jsonify
from picamera2 import Picamera2
from ultralytics import YOLO

# ── Config ────────────────────────────────────────────────────────────────────
CAPTURE_SIZE   = (640, 480)
INFER_SIZE     = 256
CONF_THRESHOLD = 0.25
JPEG_QUALITY   = 50
PORT           = 8080
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)


class LatestFrame:
    """Thread-safe single-slot buffer — stale frames are silently dropped."""
    def __init__(self):
        self._data  = None
        self._lock  = threading.Lock()
        self._event = threading.Event()

    def put(self, data):
        with self._lock:
            self._data = data
        self._event.set()

    def get(self, timeout=2.0):
        self._event.wait(timeout)
        self._event.clear()
        with self._lock:
            return self._data


latest_raw  = LatestFrame()
latest_jpeg = LatestFrame()

stats      = {"fps": 0.0, "infer_ms": 0.0, "detections": 0}
stats_lock = threading.Lock()

# Class colours (BGR) — cycles for > 8 classes
_PALETTE = [
    (  0, 200,  83), (255,  82,   0), (  0, 141, 238), (255, 196,   0),
    (218,   0, 255), (255,   0, 112), (  0, 255, 220), (178, 255,   0),
]


# ── Camera thread ─────────────────────────────────────────────────────────────
def camera_thread():
    picam2 = Picamera2()
    picam2.configure(picam2.create_video_configuration(
        main={"size": CAPTURE_SIZE, "format": "RGB888"},
    ))
    picam2.start()
    while True:
        # picamera2 gives RGB → convert to BGR once, here, for the rest of the pipeline
        # frame_bgr = cv2.cvtColor(picam2.capture_array(), cv2.COLOR_RGB2BGR)
        frame_bgr = picam2.capture_array()
        latest_raw.put(frame_bgr)


# ── Inference thread ──────────────────────────────────────────────────────────
def inference_thread():
    model = YOLO("yolov8n.pt")
    model.overrides["half"] = True   # FP16 on Pi 5 64-bit; remove if it errors

    fps_counter, fps_timer = 0, time.time()

    while True:
        frame = latest_raw.get()
        if frame is None:
            continue

        t0 = time.perf_counter()
        results = model.predict(frame, imgsz=INFER_SIZE, conf=CONF_THRESHOLD, verbose=False)[0]
        infer_ms = (time.perf_counter() - t0) * 1000

        # Draw bounding boxes onto the BGR frame
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls   = int(box.cls[0])
            conf  = float(box.conf[0])
            color = _PALETTE[cls % len(_PALETTE)]
            label = f"{model.names[cls]} {conf:.0%}"

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (x1, y1 - th - bl - 4), (x1 + tw + 4, y1), color, -1)
            cv2.putText(frame, label, (x1 + 2, y1 - bl - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Encode BGR directly — imencode treats the array as BGR and produces a
        # standard JPEG that browsers decode correctly (no extra cvtColor needed)
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        if ok:
            latest_jpeg.put(buf.tobytes())

        fps_counter += 1
        elapsed = time.time() - fps_timer
        if elapsed >= 1.0:
            with stats_lock:
                stats["fps"]        = fps_counter / elapsed
                stats["infer_ms"]   = round(infer_ms, 1)
                stats["detections"] = len(results.boxes)
            fps_counter, fps_timer = 0, time.time()


# ── HTML ──────────────────────────────────────────────────────────────────────
HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>YOLO · Live</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0 }
  :root {
    --bg:      #111113;
    --card:    #1a1a1e;
    --border:  #26262c;
    --green:   #22c55e;
    --muted:   #52525b;
    --text:    #e4e4e7;
  }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: ui-monospace, 'SF Mono', 'Menlo', monospace;
    font-size: 13px;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 24px 16px 32px;
    gap: 16px;
    min-height: 100vh;
  }

  /* ── Header ── */
  header {
    width: 100%;
    max-width: 680px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .14em;
    text-transform: uppercase;
    color: var(--muted);
  }
  .dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 6px var(--green);
    animation: pulse 2s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1 }
    50%       { opacity: .4 }
  }

  /* ── Stream ── */
  .stream {
    width: 100%;
    max-width: 680px;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid var(--border);
    background: #000;
    aspect-ratio: 4/3;
  }
  .stream img { display: block; width: 100%; height: 100%; object-fit: cover }

  /* ── Stats ── */
  .stats {
    width: 100%;
    max-width: 680px;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
  }
  .stat {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 14px 16px;
  }
  .stat-label {
    font-size: 10px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .1em;
    margin-bottom: 6px;
  }
  .stat-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text);
    line-height: 1;
  }
  .stat-unit {
    font-size: 10px;
    color: var(--muted);
    margin-top: 4px;
  }
</style>
</head>
<body>

<header>
  <span class="title">YOLOv8n · Raspberry Pi 5</span>
  <span class="dot"></span>
</header>

<div class="stream">
  <img src="/stream" alt="Live feed">
</div>

<div class="stats">
  <div class="stat">
    <div class="stat-label">FPS</div>
    <div class="stat-value" id="fps">—</div>
    <div class="stat-unit">frames / sec</div>
  </div>
  <div class="stat">
    <div class="stat-label">Inference</div>
    <div class="stat-value" id="ms">—</div>
    <div class="stat-unit">ms / frame</div>
  </div>
  <div class="stat">
    <div class="stat-label">Detections</div>
    <div class="stat-value" id="det">—</div>
    <div class="stat-unit">objects</div>
  </div>
</div>

<script>
  (function poll() {
    fetch('/stats')
      .then(r => r.json())
      .then(d => {
        document.getElementById('fps').textContent = d.fps.toFixed(1);
        document.getElementById('ms').textContent  = d.infer_ms.toFixed(0);
        document.getElementById('det').textContent = d.detections;
      })
      .catch(() => {})
      .finally(() => setTimeout(poll, 1000));
  })();
</script>
</body>
</html>"""


# ── Flask routes ──────────────────────────────────────────────────────────────
def mjpeg_stream():
    while True:
        jpeg = latest_jpeg.get()
        if jpeg is None:
            continue
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"


@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/stream")
def stream():
    return Response(mjpeg_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/stats")
def get_stats():
    with stats_lock:
        return jsonify(dict(stats))


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=camera_thread,    daemon=True).start()
    threading.Thread(target=inference_thread, daemon=True).start()
    print(f"[✓] http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True, use_reloader=False)