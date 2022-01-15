import os
import signal
from datetime import datetime
from threading import Thread
from typing import Any
from urllib.request import Request, urlopen
from wsgiref.simple_server import make_server

import click

from offstream import db
from offstream.streaming import Recorder


@click.group("offstream", invoke_without_command=True)
@click.pass_context
@click.option("--host", help="Bind host", default="127.0.0.1", show_default=True)
@click.option("-p", "--port", help="Bind port", default=8000, show_default=True)
def main(ctx: click.core.Context, host: str, port: int) -> None:
    """Start offstream."""

    if ctx.invoked_subcommand is not None:
        return

    from offstream.app import app

    httpd = make_server(host, port, app)
    server = Thread(target=httpd.serve_forever)
    server.start()
    try:
        ctx.invoke(record)
    finally:
        httpd.shutdown()
        server.join()


@main.command("record")
def record() -> None:
    """Start stream recorder only."""

    def close_recorder(*args: Any) -> None:
        recorder.close()

    recorder = Recorder()
    signal.signal(signal.SIGINT, close_recorder)
    signal.signal(signal.SIGTERM, close_recorder)
    recorder.start()


@main.command("create")
def create() -> None:
    """Create db tables."""
    db.Base.metadata.create_all(db.engine)


@main.command("setup")
@click.option("-u", "--app-url", help="App URL to ping", required=True)
@click.pass_context
def setup(ctx: click.core.Context, app_url: str) -> None:
    """Setup the database."""
    ctx.invoke(create)

    # TODO: Make app_url optional. If it's missing, don't ping itself.
    settings, password = db.settings(app_url=app_url)
    username = settings.username
    with db.Session() as session:
        if not session.query(db.Settings).scalar():
            session.add(settings)
            session.commit()
            print(f"Username: {username}")
            print(f"Password: {password}")


@main.command("ping")
def ping() -> None:
    """Ping itself to prevent idling."""
    start_hour = int(os.getenv("OFFSTREAM_AWAKE_START_HOUR", "0"))
    end_hour = int(os.getenv("OFFSTREAM_AWAKE_END_HOUR", "24"))
    now = datetime.now()
    with db.Session() as session:
        streamers_exist = session.scalars(db.streamers()).first() is not None
        settings = session.query(db.Settings).scalar()
    # TODO: support pings from, say, 22 to 7.
    if streamers_exist and settings and start_hour <= now.hour < end_hour:
        request = Request(settings.app_url, headers={"user-agent": "offstream-ping"})
        with urlopen(request) as response:  # nosec
            print(response.msg)
    else:
        print("Skipped")
