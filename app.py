import os
import urllib.request

from flask import Flask, redirect, abort

from db import latest_stream

app = Flask(__name__)


@app.route("/latest/<name>")
def index(name):
    stream = latest_stream(name)

    if stream:
        m3u8 = urllib.request.urlopen(stream.url).read()
        return (m3u8, 200, {"content-type": "application/vnd.apple.mpegurl"})
    else:
        abort(404, "No streams found")
