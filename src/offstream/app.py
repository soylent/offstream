import datetime as dt
from typing import Any

from flask import Flask, abort, make_response, render_template, request
from flask.typing import ResponseReturnValue
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash

from offstream import db
from offstream.cli import main

app = Flask("offstream", static_url_path="/")
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
app.cli.add_command(main)

# TODO: GET /settings
# TODO: Tests - test the recorder package
# - no internet connection before
# - no internet connection while recording
# TODO: Streams don't open on iOS
# TODO: When a stream ends, this error occurs 4 times
# Failed to reload playlist: Unable to open URL: https://video-weaver.ord03.hls.ttvnw.net/v1/playlist/CpQE3n8aIVIv4MWfbjTli_AhPW3hWuLDPBvj24uLcojVTyD3WRUjlOdmAntDTIu-UR2WiILz8-k_zqJ5eLZYtFNBYyGbcfg7CN72qzqXfAGG899ZgzmAPmoqHN2E8AMe9QgFax8LapmwlygvclnYxby6GSszZ_mUxbQ4IQU9IwGSJcXiPX2rFI9OSlAt5I4NjZWAd-GNHyrmeIwTMEKelGhcdtja_sZLMzhBNR62T23mzfQB01slO9B_nKYVwDeDAir0X3P6Qd2AK_55FkCx0te8HUzia5mZFFY3-YEU4QiY8ia1lpKDbkvdFKutV09m1x7oYfEtpChcoGEf-31mu5a7fZW4nlb_yGwNw3MyGdAn6jExoTZR-QlaZjcJHi-46Wi8LSP3ki8_gj_-A1u-eP7I4B9bo8ooL5TJ11QoqP33-uUZsfxuQO5ZTH6qHQLva-hZBIF0w6_KB_-QVi_LH-t8qY5Wm03BcnThVe6Zy7vreaec0i2sc5IAQ6iBrMx_Bbur2hN_Ks82bgUVBNfptZlb4Lp9oExHgfruyxBXQCl79b207-RzmqZLPXsjIzxwwAEFpaiTvQAGaf2xpKbUE27e5Dpmxuc2EggYoJy-I-bI8NL0Z0q9_jBs8RDIA0iT7bySDhdIFmFXf1yUc5khl20jHpEdBQ1I5TICGgw_OnLZ-rH0O-LbI2WZlvmsItWBhVDtdnDjYhoMqy7CDhESwZw_DfYDIAEqCXVzLWVhc3QtMjDQAg.m3u8 (404 Client Error: Not Found for url: https://video-weaver.ord03.hls.ttvnw.net/v1/playlist/CpQE3n8aIVIv4MWfbjTli_AhPW3hWuLDPBvj24uLcojVTyD3WRUjlOdmAntDTIu-UR2WiILz8-k_zqJ5eLZYtFNBYyGbcfg7CN72qzqXfAGG899ZgzmAPmoqHN2E8AMe9QgFax8LapmwlygvclnYxby6GSszZ_mUxbQ4IQU9IwGSJcXiPX2rFI9OSlAt5I4NjZWAd-GNHyrmeIwTMEKelGhcdtja_sZLMzhBNR62T23mzfQB01slO9B_nKYVwDeDAir0X3P6Qd2AK_55FkCx0te8HUzia5mZFFY3-YEU4QiY8ia1lpKDbkvdFKutV09m1x7oYfEtpChcoGEf-31mu5a7fZW4nlb_yGwNw3MyGdAn6jExoTZR-QlaZjcJHi-46Wi8LSP3ki8_gj_-A1u-eP7I4B9bo8ooL5TJ11QoqP33-uUZsfxuQO5ZTH6qHQLva-hZBIF0w6_KB_-QVi_LH-t8qY5Wm03BcnThVe6Zy7vreaec0i2sc5IAQ6iBrMx_Bbur2hN_Ks82bgUVBNfptZlb4Lp9oExHgfruyxBXQCl79b207-RzmqZLPXsjIzxwwAEFpaiTvQAGaf2xpKbUE27e5Dpmxuc2EggYoJy-I-bI8NL0Z0q9_jBs8RDIA0iT7bySDhdIFmFXf1yUc5khl20jHpEdBQ1I5TICGgw_OnLZ-rH0O-LbI2WZlvmsItWBhVDtdnDjYhoMqy7CDhESwZw_DfYDIAEqCXVzLWVhc3QtMjDQAg.m3u8)


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
        query = select(db.Streamer).where(db.Streamer.name == name)
        streamer = session.scalars(query).one_or_none()
        if not streamer:
            abort(404, "Streamer not found")
        session.delete(streamer)
        session.commit()
        return _serialize_streamer(streamer)


@app.post("/settings")
def update_settings() -> ResponseReturnValue:
    require_auth()
    with db.Session() as session:
        settings = session.query(db.Settings).scalar()
        assert settings
        for attr in ("ping_start_hour", "ping_end_hour"):
            if value := request.form.get(attr):
                try:
                    setattr(settings, attr, value)
                except ValueError as error:
                    session.rollback()
                    abort(422, str(error))
        session.commit()
        return {
            "username": settings.username,
            "password": "<REDUCTED>",
            "ping_url": settings.ping_url,
            "ping_start_hour": settings.ping_start_hour,
            "ping_end_hour": settings.ping_end_hour,
        }


# TODO: Make limit a query param
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
    db.Base.metadata.create_all(db.engine)
    with db.Session() as session:
        if session.query(db.Settings).scalar():
            abort(409, "This app has already been claimed.")
        settings, password = db.settings(ping_url=request.host_url)
        username = settings.username
        session.add(settings)
        session.commit()
    html = render_template("welcome.html", username=username, password=password)
    return make_response(html)


@app.errorhandler(HTTPException)
def handle_error(error: HTTPException) -> ResponseReturnValue:
    return {
        "error": {"name": error.name.lower(), "description": error.description}
    }, error.code


@app.template_filter("rfc822")
def rfc822(value: dt.datetime, timezone: dt.timezone = dt.timezone.utc) -> str:
    timetz = value.replace(tzinfo=timezone).astimezone()
    return timetz.strftime("%a, %d %b %Y %H:%M:%S %z")


def require_auth() -> None:
    if not request.authorization or request.authorization.type != "basic":
        abort(401, "Authentication failed")
    username = request.authorization.username
    password = request.authorization.password
    with db.Session() as session:
        settings = session.query(db.Settings).scalar()
        if (
            settings
            and username == settings.username
            and password
            and check_password_hash(settings.password, password)
        ):
            return  # Pass
    abort(401, "Authentication failed")


def _serialize_streamer(streamer: db.Streamer) -> dict[str, Any]:
    return {
        "id": streamer.id,
        "name": streamer.name,
        "url": streamer.url,
        "max_quality": streamer.max_quality,
    }
