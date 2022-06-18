from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, inspect

import offstream
from offstream import db


@pytest.mark.parametrize("command", ["offstream", "offstream record"])
def test_main(runner, command):
    with patch("offstream.cli.Recorder") as recorder:
        recorder.return_value.start.return_value = None
        result = runner.invoke(args=command)

    assert result.exit_code == 0
    if command == "offstream":
        assert "Running on http://127.0.0.1:8000/" in result.stdout
    elif command == "offstream record":
        assert not result.output
    else:
        assert False


@pytest.mark.parametrize("port", [-1, 65536])
def test_main_when_port_is_invalid(runner, port):
    result = runner.invoke(args=["offstream", "--port", port])

    assert result.exit_code == 2
    assert "Invalid value" in result.output


def test_main_when_host_is_invalid(runner):
    result = runner.invoke(args=["offstream", "--host", "oiujif"])

    assert result.exit_code == 1
    assert "Bind failed" in result.output


def test_version(runner):
    result = runner.invoke(args=["offstream", "--version"])

    assert result.exit_code == 0
    assert str(offstream.__version__) in result.output


@pytest.fixture
def set_time():
    def _set_time(*, hour):
        datetime.now.return_value.hour = hour

    with patch("offstream.cli.datetime") as datetime:
        yield _set_time


@pytest.fixture
def set_ping_hours(settings, session):
    def _set_ping_hours(*, start_hour, end_hour):
        settings.ping_start_hour = start_hour
        settings.ping_end_hour = end_hour
        session.commit()

    settings = settings[0]
    yield _set_ping_hours


@pytest.mark.parametrize(
    "params",
    [
        {"start_hour": 0, "current_hour": 0, "end_hour": 24, "ping": True},
        {"start_hour": 22, "current_hour": 22, "end_hour": 7, "ping": True},
        {"start_hour": 22, "current_hour": 0, "end_hour": 7, "ping": True},
        {"start_hour": 0, "current_hour": 22, "end_hour": 22, "ping": False},
        {"start_hour": 22, "current_hour": 21, "end_hour": 7, "ping": False},
        {"start_hour": 22, "current_hour": 7, "end_hour": 7, "ping": False},
        {"start_hour": 0, "current_hour": 0, "end_hour": 0, "ping": False},
    ],
)
def test_ping_during_on_and_off_hours(
    runner, streamer, set_ping_hours, set_time, params
):
    set_ping_hours(start_hour=params["start_hour"], end_hour=params["end_hour"])
    set_time(hour=params["current_hour"])

    with patch("offstream.cli.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.msg = "OK"
        result = runner.invoke(args=["offstream", "ping"])

        assert result.exit_code == 0

        if params["ping"]:
            urlopen.assert_called_once()
            assert "OK" in result.stdout
        else:
            urlopen.assert_not_called()
            assert "Skipped" in result.stdout


def test_ping_when_there_are_no_streamers(runner, settings):
    result = runner.invoke(args=["offstream", "ping"])

    assert result.exit_code == 0
    assert "Skipped" in result.stdout


def test_ping_when_there_are_no_settings(runner, streamer):
    result = runner.invoke(args=["offstream", "ping"])

    assert result.exit_code == 0
    assert "Skipped" in result.stdout


def test_init_db_success(runner):
    result = runner.invoke(args=["offstream", "init-db"])

    assert inspect(db.engine).get_table_names()
    assert result.exit_code == 0
    assert not result.output


def test_init_db_failure(runner, monkeypatch):
    bad_engine = create_engine("sqlite:////")
    try:
        with patch.object(offstream.cli.db, "engine", new=bad_engine) as engine:
            result = runner.invoke(args=["offstream", "init-db"])
    finally:
        bad_engine.dispose()

    assert result.exit_code == 1
    assert "unable to open database file" in result.output


def test_setup(runner):
    command = ["offstream", "setup"]
    result = runner.invoke(args=command)

    assert inspect(db.engine).get_table_names()
    assert result.exit_code == 0
    assert "Username" in result.stdout
    assert "Password" in result.stdout

    result = runner.invoke(args=command)

    assert result.exit_code == 0
    assert not result.output
