import signal
from datetime import datetime
from threading import Thread
from typing import Any, Callable
from urllib.request import Request, urlopen
from wsgiref.simple_server import make_server

import click
from sqlalchemy import select

from offstream import db
from offstream.streaming import Recorder


def validate_within(
    minval: int, maxval: int
) -> Callable[[click.core.Context, str, int], int]:
    def _validator(ctx: click.core.Context, param: str, value: int) -> int:
        if minval <= value <= maxval:
            return value
        raise click.BadParameter(f"must be within {minval}-{maxval}")

    return _validator


@click.group("offstream", invoke_without_command=True)
@click.pass_context
@click.option("--host", help="Bind host", default="127.0.0.1", show_default=True)
@click.option(
    "-p",
    "--port",
    help="Bind port",
    default=8000,
    show_default=True,
    callback=validate_within(0, 63535),
)
def main(ctx: click.core.Context, host: str, port: int) -> None:
    """Start offstream."""

    if ctx.invoked_subcommand is not None:
        return

    from offstream.app import app

    try:
        httpd = make_server(host, port, app)
    except OSError as error:
        raise click.ClickException(f"Bind failed: {error}") from error
    bind_host, bind_port = httpd.server_address
    click.echo(f"Running on http://{bind_host}:{bind_port}/")
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

    def close_recorder(*_args: Any) -> None:
        recorder.close()

    recorder = Recorder()
    signal.signal(signal.SIGINT, close_recorder)
    signal.signal(signal.SIGTERM, close_recorder)
    recorder.start()


@main.command("db-init")
def db_init() -> None:
    """Create db tables."""
    db.Base.metadata.create_all(db.engine)


@main.command("setup")
@click.pass_context
def setup(ctx: click.core.Context) -> None:
    """Setup offstream."""
    ctx.invoke(db_init)
    with db.Session() as session:
        if not session.query(db.Settings).scalar():
            settings, password = db.settings()
            username = settings.username
            session.add(settings)
            session.commit()
            click.echo(f"Username: {username}")
            click.echo(f"Password: {password}")


@main.command("ping")
def ping() -> None:
    now = datetime.now()
    with db.Session() as session:
        streamers_exist = session.scalars(select(db.Streamer)).first() is not None
        settings = session.query(db.Settings).scalar()
    if streamers_exist and settings and settings.ping_url:
        start_hour = settings.ping_start_hour
        end_hour = settings.ping_end_hour
        on = start_hour <= now.hour < end_hour
        not_off = end_hour < start_hour and not end_hour <= now.hour < start_hour
        if on or not_off:
            request = Request(
                settings.ping_url, headers={"user-agent": "offstream-ping"}
            )
            with urlopen(request) as response:  # nosec
                click.echo(response.msg)
            return
    click.echo("Skipped")
