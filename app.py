import os

from flask import Flask, redirect

from db import latest_recording

app = Flask(__name__)


@app.route("/latest/<name>")
def index(name):
    recording = latest_recording(name)

    return redirect(recording.url, code=303)
