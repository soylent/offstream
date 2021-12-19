import os

import flask

flask.cli.load_dotenv()
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from offstream import db
from offstream.app import app


@pytest.fixture
def setup_db():
    db.Base.metadata.create_all(db.engine)
    yield
    db.Base.metadata.drop_all(db.engine)


@pytest.fixture
def session():
    with db.Session() as session:
        yield session


@pytest.fixture
def client(setup_db):
    app.testing = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def runner(setup_db):
    return app.test_cli_runner()


@pytest.fixture
def settings(session):
    settings, password = db.settings(app_url="https://example.org/")
    session.add(settings)
    session.commit()
    return settings, password


@pytest.fixture
def auth(settings):
    settings_, password = settings
    return settings_.username, password


@pytest.fixture
def stream(session):
    streamer = db.Streamer(name="x")
    stream_ = db.Stream(
        title="y", category="z", url="https://example.org/", streamer=streamer
    )
    session.add(stream_)
    session.commit()
    return stream_


@pytest.fixture(params=[None, ("offstream", ""), ("offstream", "wrong")])
def bad_auth(request):
    return request.param


@pytest.fixture
def m3u8(tmpdir):
    return tmpdir.join("playlist.m3u8")
