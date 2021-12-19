import pytest
from offstream import db
from sqlalchemy import inspect


def test_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_not_found(client):
    response = client.get("/x")

    assert response.status_code == 404
    assert response.json["error"]["name"] == "not found"
    assert response.json["error"]["description"]


def test_method_not_allowed(client):
    response = client.post("/")

    assert response.status_code == 405
    assert response.json["error"]["name"] == "method not allowed"
    assert response.json["error"]["description"]


def test_latest_stream(client, stream):
    response = client.get(f"/latest/{stream.streamer.name}")

    assert response.status_code == 302
    assert response.location.startswith("https://")
    assert response.json["url"] == response.location


def test_latest_stream_for_non_existent_streamer(client):
    response = client.get("/latest/nonexistent")

    assert response.status_code == 404
    assert response.json["error"]["name"] == "not found"
    assert response.json["error"]["description"] == "No streams found"


@pytest.mark.parametrize("name", ["x", "X"])
def test_create_streamer(client, name, auth):
    response = client.post("/streamers", data={"name": name}, auth=auth)

    assert response.status_code == 201
    assert response.json["id"]
    assert response.json["name"] == "x"
    assert response.json["quality"] == "best"
    assert response.json["url"] == "https://twitch.tv/x"


def test_create_streamer_dupliacate(client, auth):
    for _ in range(2):
        response = client.post("/streamers", data={"name": "x"}, auth=auth)

    assert response.status_code == 409
    assert response.json["error"]["name"] == "conflict"
    assert response.json["error"]["description"] == "Duplicate streamer URL"


def test_create_streamer_auth(client, bad_auth, settings):
    response = client.post("/streamers", auth=bad_auth)

    assert response.status_code == 401
    assert response.json["error"]["name"] == "unauthorized"
    assert response.json["error"]["description"] == "Authentication failed"


@pytest.mark.parametrize("name", [None, ""])
def test_create_streamer_with_invalid_name(client, name, auth):
    response = client.post("/streamers", data={"name": name}, auth=auth)

    assert response.status_code == 422
    assert response.json["error"]["name"] == "unprocessable entity"
    assert response.json["error"]["description"] == "Missing streamer name"


@pytest.mark.parametrize("quality", ["", "0"])
def test_create_streamer_with_invalid_quality(client, quality, auth):
    response = client.post(
        "/streamers", data={"name": "x", "quality": quality}, auth=auth
    )

    assert response.status_code == 422
    assert response.json["error"]["name"] == "unprocessable entity"
    assert response.json["error"]["description"] == f"Invalid stream quality: {quality}"


def test_delete_streamer(client, stream, session, auth):
    streamer = stream.streamer
    response = client.delete(f"/streamers/{streamer.name}", auth=auth)

    session.expunge_all()
    assert not session.get(db.Streamer, streamer.id)
    assert not session.get(db.Stream, stream.id)

    assert response.status_code == 200
    assert response.json["id"] == streamer.id
    assert response.json["name"] == streamer.name
    assert response.json["quality"] == streamer.quality
    assert response.json["url"] == streamer.url


def test_delete_not_found(client, auth):
    response = client.delete("/streamers/nonexistent", auth=auth)

    assert response.status_code == 404
    assert response.json["error"]["name"] == "not found"
    assert response.json["error"]["description"] == "Streamer not found"


def test_delete_streamer_auth(client, stream, bad_auth):
    streamer = stream.streamer
    response = client.delete(f"/streamers/{streamer.name}", auth=bad_auth)

    assert response.status_code == 401
    assert response.json["error"]["name"] == "unauthorized"
    assert response.json["error"]["description"] == "Authentication failed"


@pytest.mark.parametrize("fixture", [None, "stream"])
def test_rss(client, fixture, request):
    if fixture:
        request.getfixturevalue(fixture)

    response = client.get("/rss")

    assert response.status_code == 200
    assert response.content_type == "application/rss+xml"
    assert response.data


def test_welcome(client):
    response = client.get("/welcome")

    assert inspect(db.engine).get_table_names()
    assert response.status_code == 200
    assert b"Username" in response.data
    assert b"Password" in response.data

    response = client.get("/welcome")

    assert response.status_code == 409
    assert b"This app has already been claimed." in response.data


def test_robots(client):
    response = client.get("/robots.txt")

    assert response.status_code == 200
    assert b"Disallow: /" in response.data


def test_favicon(client):
    response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert response.data
