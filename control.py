from flask import Flask, render_template_string
import subprocess
import os
import signal

app = Flask(__name__)

STREAM_CMD = ["python3", "/home/pi/stream/stream.py"]
stream_process = None

HTML = """
<h1>Pi Camera Control</h1>

<form action="/start" method="post">
    <button type="submit">Start Stream</button>
</form>

<form action="/stop" method="post">
    <button type="submit">Stop Stream</button>
</form>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/start", methods=["POST"])
def start():
    global stream_process
    if stream_process is None:
        stream_process = subprocess.Popen(STREAM_CMD)
    return "Stream started <a href='/'>back</a>"

@app.route("/stop", methods=["POST"])
def stop():
    global stream_process
    if stream_process:
        stream_process.send_signal(signal.SIGTERM)
        stream_process = None
    return "Stream stopped <a href='/'>back</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
