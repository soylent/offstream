import pytest
from sqlalchemy import inspect

from offstream import db


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
    assert response.access_control_allow_origin == "*"
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
    assert response.json["max_quality"] == "best"
    assert response.json["url"] == "https://twitch.tv/x"


def test_create_streamer_dupliacate(client, auth):
    for _ in range(2):
        response = client.post("/streamers", data={"name": "x"}, auth=auth)

    assert response.status_code == 409
    assert response.json["error"]["name"] == "conflict"
    assert response.json["error"]["description"] == "Duplicate streamer URL"


@pytest.mark.parametrize("name", [None, ""])
def test_create_streamer_with_invalid_name(client, name, auth):
    response = client.post("/streamers", data={"name": name}, auth=auth)

    assert response.status_code == 422
    assert response.json["error"]["name"] == "unprocessable entity"
    assert response.json["error"]["description"] == "Missing streamer name"


@pytest.mark.parametrize("max_quality", ["", "0"])
def test_create_streamer_with_invalid_max_quality(client, max_quality, auth):
    response = client.post(
        "/streamers", data={"name": "x", "max_quality": max_quality}, auth=auth
    )

    assert response.status_code == 422
    assert response.json["error"]["name"] == "unprocessable entity"
    assert (
        response.json["error"]["description"]
        == f"Invalid max stream quality: {max_quality}"
    )


def test_delete_streamer(client, stream, session, auth):
    streamer = stream.streamer
    response = client.delete(f"/streamers/{streamer.name}", auth=auth)

    session.expunge_all()
    assert not session.get(db.Streamer, streamer.id)
    assert not session.get(db.Stream, stream.id)

    assert response.status_code == 200
    assert response.json["id"] == streamer.id
    assert response.json["name"] == streamer.name
    assert response.json["max_quality"] == streamer.max_quality
    assert response.json["url"] == streamer.url


def test_delete_not_found(client, auth):
    response = client.delete("/streamers/nonexistent", auth=auth)

    assert response.status_code == 404
    assert response.json["error"]["name"] == "not found"
    assert response.json["error"]["description"] == "Streamer not found"


def test_update_ping_hours(client, auth, settings):
    data = {"ping_start_hour": 1, "ping_end_hour": 2}
    response = client.post("/settings", auth=auth, data=data)

    assert response.status_code == 200
    assert response.json["ping_start_hour"] == data["ping_start_hour"]
    assert response.json["ping_end_hour"] == data["ping_end_hour"]


@pytest.mark.parametrize("param", ["ping_start_hour", "ping_end_hour"])
@pytest.mark.parametrize("value", [-1, 25, "x"])
def test_update_ping_hours_with_invalid_values(client, auth, param, value):
    response = client.post("/settings", auth=auth, data={param: value})

    assert response.status_code == 422
    assert response.json["error"]["name"] == "unprocessable entity"
    assert "Invalid hour" in response.json["error"]["description"]


@pytest.mark.parametrize(
    "endpoint",
    [
        {"method": "POST", "path": "/streamers"},
        {"method": "DELETE", "path": "/streamers/anything"},
        {"method": "POST", "path": "/settings"},
    ],
)
@pytest.mark.parametrize("fixture", [None, "settings"])
def test_auth(client, bad_auth, endpoint, fixture, request):
    if fixture:
        request.getfixturevalue(fixture)

    response = client.open(**endpoint, auth=bad_auth)

    assert response.status_code == 401
    assert response.json["error"]["name"] == "unauthorized"
    assert response.json["error"]["description"] == "Authentication failed"


@pytest.mark.parametrize("fixture", [None, "stream"])
@pytest.mark.parametrize("limit", ["1", None])
def test_rss(client, fixture, limit, request):
    if fixture:
        request.getfixturevalue(fixture)

    response = client.get("/rss", query_string={"limit": limit})

    assert response.status_code == 200
    assert response.content_type == "application/rss+xml"
    assert response.data


@pytest.mark.parametrize("limit", ["", "x"])
def test_invalid_rss_limit(client, limit):
    response = client.get("/rss", query_string={"limit": limit})

    assert response.status_code == 400
    assert b"Invalid limit" in response.data


def test_welcome(client):
    response = client.get("/welcome")

    assert inspect(db.engine).get_table_names()
    assert response.status_code == 200
    assert b"Username" in response.data
    assert b"Password" in response.data

    response = client.get("/welcome")

    assert response.status_code == 409
    assert b"This app has already been claimed." in response.data


def test_welcome_on_heroku(client):
    response = client.get("/welcome", headers={"host": "abc.herokuapp.com"})

    assert response.status_code == 200
    assert b"abc" in response.data
    assert b"offstream ping" in response.data


def test_welcome_on_non_heroku(client):
    response = client.get("/welcome", headers={"host": "example.org"})

    assert response.status_code == 200
    assert b"offstream ping" not in response.data


def test_robots(client):
    response = client.get("/robots.txt")

    assert response.status_code == 200
    assert b"Disallow: /" in response.data


def test_favicon(client):
    response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert response.data
