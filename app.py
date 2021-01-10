import os
import subprocess

from flask import Flask, send_from_directory, url_for

app = Flask(__name__)


@app.route("/")
def index():
    videos = []
    for video in sorted(os.listdir("files")):
        if video.startswith(".") or video.endswith(".part"):
            continue
        videos.append(url_for("download_file", _external=True, filename=video))
    return "\n".join(videos), {"content-type": "text/plain"}


@app.route("/v/<path:filename>")
def download_file(filename):
    return send_from_directory("files", filename, as_attachment=True)
