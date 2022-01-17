from unittest.mock import patch

import pytest
from sqlalchemy import inspect

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


@pytest.mark.parametrize("port", [-1, 65536])
def test_main_when_port_is_invalid(runner, port):
    result = runner.invoke(args=["offstream", "--port", port])

    assert result.exit_code == 2
    assert "Invalid value" in result.output


def test_main_when_host_is_invalid(runner):
    result = runner.invoke(args=["offstream", "--host", "oiujif"])

    assert result.exit_code == 1
    assert "Bind failed" in result.output


@pytest.fixture
def set_time():
    def _set_time(*, hour):
        datetime.now.return_value.hour = hour

    with patch("offstream.cli.datetime") as datetime:
        yield _set_time


@pytest.mark.parametrize("hours", [(0, 0, 24), (22, 22, 7), (22, 0, 7)])
def test_ping_during_on_hours(runner, streamer, settings, set_time, session, hours):
    settings = settings[0]
    start, now, end = hours
    settings.ping_start_hour = start
    settings.ping_end_hour = end
    session.commit()
    set_time(hour=now)

    with patch("offstream.cli.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.msg = "OK"
        result = runner.invoke(args=["offstream", "ping"])

    assert result.exit_code == 0
    assert "OK" in result.stdout


@pytest.mark.parametrize("hours", [(0, 22, 22), (22, 21, 7), (22, 7, 7), (0, 0, 0)])
def test_ping_during_off_hours(runner, streamer, settings, set_time, session, hours):
    start, now, end = hours
    settings = settings[0]
    settings.ping_start_hour = start
    settings.ping_end_hour = end
    session.commit()
    set_time(hour=now)

    result = runner.invoke(args=["offstream", "ping"])

    assert result.exit_code == 0
    assert "Skipped" in result.stdout


def test_ping_when_there_are_no_streamers(runner, settings):
    result = runner.invoke(args=["offstream", "ping"])

    assert result.exit_code == 0
    assert "Skipped" in result.stdout


def test_ping_when_there_are_no_settings(runner, streamer):
    result = runner.invoke(args=["offstream", "ping"])

    assert result.exit_code == 0
    assert "Skipped" in result.stdout


def test_db_init(runner):
    result = runner.invoke(args=["offstream", "db-init"])

    assert inspect(db.engine).get_table_names()
    assert result.exit_code == 0
    assert not result.output


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
