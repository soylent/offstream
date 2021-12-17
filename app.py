import os

from flask import Flask, abort, redirect, request

from db import create_streamer, latest_stream

app = Flask(__name__)


@app.route("/latest/<name>")
def latest_stream_(name):
    stream = latest_stream(name)

    if stream:
        return redirect(stream.url)
    else:
        return {"error": "no streams found"}, 404


@app.route("/streamers", methods=["POST"])
def create_streamer_():
    # TODO: already exists
    # TODO: invaild url
    # TODO: invalid quality
    # TODO: missing params x 2 - try pydantic
    url = request.form.get("url")
    quality = request.form.get("quality")

    create_streamer(url, quality)

    return {"url": url, "quality": quality}, 201
