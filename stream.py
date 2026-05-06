from picamera2 import Picamera2
from flask import Flask, Response
from ultralytics import YOLO
import cv2
import io
from PIL import Image

app = Flask(__name__)

# Load lightweight model (fast on Pi 5)
model = YOLO("yolov8n.pt")

picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
picam2.start()


def generate():
    while True:
        frame = picam2.capture_array()

        # YOLO expects BGR
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Run detection
        results = model(frame_bgr, verbose=False)[0]

        # Draw boxes
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            label = f"{model.names[cls]} {conf:.2f}"

            cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame_bgr, label, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (0, 255, 0), 1)

        # Convert back for browser
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=80)
        jpeg = buf.getvalue()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')


@app.route('/')
def video():
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


app.run(host='0.0.0.0', port=8080)
