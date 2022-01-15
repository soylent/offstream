from unittest.mock import patch

import pytest
from offstream import db
from sqlalchemy import inspect


@pytest.mark.parametrize("command", [("offstream"), ("offstream", "record")])
def test_main(runner, command):
    with patch("offstream.cli.Recorder") as recorder:
        recorder.return_value.start.return_value = None
        result = runner.invoke(args=command)

    assert result.exit_code == 0
    assert not result.output


def test_ping_when_there_are_streamers(runner, stream, settings):
    with patch("offstream.cli.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.msg = "OK"
        result = runner.invoke(args=["offstream", "ping"])

    assert result.exit_code == 0
    assert "OK" in result.stdout


def test_ping_during_off_hours(runner, stream, settings):
    result = runner.invoke(
        args=["offstream", "ping"],
        env={"OFFSTREAM_AWAKE_START_HOUR": "0", "OFFSTREAM_AWAKE_END_HOUR": "0"},
    )

    assert result.exit_code == 0
    assert "Skipped" in result.stdout


def test_ping_when_there_are_no_streamers(runner, settings):
    result = runner.invoke(args=["offstream", "ping"])

    assert result.exit_code == 0
    assert "Skipped" in result.stdout


def test_ping_when_there_are_no_settings(runner, stream):
    result = runner.invoke(args=["offstream", "ping"])

    assert result.exit_code == 0
    assert "Skipped" in result.stdout


def test_create(runner):
    result = runner.invoke(args=["offstream", "create"])

    assert inspect(db.engine).get_table_names()
    assert result.exit_code == 0
    assert not result.output


def test_setup(runner):
    args = ["offstream", "setup", "--app-url", "https://example.org"]
    result = runner.invoke(args=args)

    assert inspect(db.engine).get_table_names()
    assert result.exit_code == 0
    assert "Username" in result.output
    assert "Password" in result.output

    result = runner.invoke(args=args)

    assert result.exit_code == 0
    assert not result.output
