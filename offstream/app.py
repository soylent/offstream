import datetime as dt
from typing import Any

from flask import Flask, abort, make_response, render_template, request
from flask.typing import ResponseReturnValue
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash

from offstream import db
from offstream.cli import cli

app = Flask("offstream", static_url_path="/")
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
app.cli.add_command(cli)

# TODO: Tests - test the recorder package
# - non existent streamer
# - no internet connection before
# - no internet connection while recording

# TODO: Refactor process_sequence - define my own worker class?
# TODO: Distribute as a package? Easy to install and run on any server


@app.get("/")
def root() -> ResponseReturnValue:
    return {"status": "ok"}


@app.get("/latest/<name>")
def latest_stream(name: str) -> ResponseReturnValue:
    with db.Session() as session:
        if stream := session.scalars(db.latest_streams(name)).first():
            return {"url": stream.url}, 302, {"location": stream.url}

    abort(404, "No streams found")


@app.post("/streamers")
def create_streamer() -> ResponseReturnValue:
    require_auth()
    name = request.form.get("name")
    max_quality = request.form.get("max_quality")
    try:
        streamer = db.Streamer(name=name, max_quality=max_quality)
    except ValueError as error:
        abort(422, str(error))
    with db.Session() as session:
        session.add(streamer)
        try:
            session.commit()
        except IntegrityError:
            abort(409, "Duplicate streamer URL")
        return _serialize_streamer(streamer), 201


@app.delete("/streamers/<name>")
def delete_streamer(name: str) -> ResponseReturnValue:
    require_auth()
    with db.Session() as session:
        streamer = session.scalars(db.streamer(name)).one_or_none()
        if not streamer:
            abort(404, "Streamer not found")
        session.delete(streamer)
        session.commit()
        return _serialize_streamer(streamer)



@app.get("/rss")
def rss(limit: int = 20) -> ResponseReturnValue:
    with db.Session() as session:
        streams = session.scalars(db.latest_streams(limit=limit)).all()
    xml = render_template("rss.xml", streams=streams)
    response = make_response(xml)
    response.content_type = "application/rss+xml"
    return response


@app.get("/welcome")
def welcome() -> ResponseReturnValue:
    settings, password = db.settings(app_url=request.host_url)
    username = settings.username
    with db.Session() as session:
        if session.query(db.Settings).scalar():
            abort(409, "This app has already been claimed.")
        session.add(settings)
        session.commit()
    html = render_template("welcome.html", username=username, password=password)
    return make_response(html)


@app.errorhandler(HTTPException)
def handle_error(error: HTTPException) -> ResponseReturnValue:
    return {"error": {"name": error.name.lower(), "description": error.description}}, error.code


@app.template_filter("rfc822")
def rfc822(value: dt.datetime, timezone: dt.timezone = dt.timezone.utc) -> str:
    return value.replace(tzinfo=timezone).astimezone().strftime("%a, %d %b %Y %H:%M:%S %z")


def require_auth() -> None:
    if not request.authorization or request.authorization.type != "basic":
        abort(401, "Authentication failed")
    username = request.authorization.username
    password = request.authorization.password
    with db.Session() as session:
        settings = session.query(db.Settings).scalar()
        if settings and username == settings.username and password and check_password_hash(settings.password, password):
            return  # pass
    abort(401, "Authentication failed")


def _serialize_streamer(streamer: db.Streamer) -> dict[str, Any]:
    return { "id": streamer.id, "name": streamer.name, "url": streamer.url, "max_quality": streamer.max_quality }
