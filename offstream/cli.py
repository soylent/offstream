import os
import secrets
import signal
import string
from datetime import datetime
from typing import Any
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import click
from flask.cli import AppGroup

from offstream import db
from offstream.streaming import Recorder

cli = AppGroup("offstream")


@cli.command("ping")
def ping() -> None:
    """Ping itself to prevent idling."""
    start_hour = int(os.getenv("OFFSTREAM_AWAKE_START_HOUR", "0"))
    end_hour = int(os.getenv("OFFSTREAM_AWAKE_END_HOUR", "24"))
    now = datetime.now()
    with db.Session() as session:
        streamers_exist = session.scalars(db.streamers()).first() is not None
        settings = session.query(db.Settings).scalar()
    if streamers_exist and settings and start_hour <= now.hour < end_hour:
        request = Request(settings.app_url, headers={"user-agent": "offstream-ping"})
        with urlopen(request) as response:  # nosec
            print(response.msg)
    else:
        print("Skipped")


@cli.command("record")
def record() -> None:
    """Start stream recorder."""
    def close_recorder(*args: Any) -> None:
        recorder.close()

    recorder = Recorder()
    signal.signal(signal.SIGINT, close_recorder)
    signal.signal(signal.SIGTERM, close_recorder)
    recorder.start()


@cli.command("create")
def create() -> None:
    """Create db tables."""
    db.Base.metadata.create_all(db.engine)


@cli.command("setup")
@click.option("-u", "--app-url", help="App URL to ping", required=True)
@click.pass_context
def setup(ctx: click.core.Context, app_url: str) -> None:
    """Setup the database."""
    ctx.invoke(create)

    settings, password = db.settings(app_url=app_url)
    username = settings.username
    with db.Session() as session:
        if not session.query(db.Settings).scalar():
            session.add(settings)
            session.commit()
            print(f"Username: {username}")
            print(f"Password: {password}")
