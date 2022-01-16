import os
import re
import secrets
import string
from pathlib import Path
from typing import Optional

from click import get_app_dir
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
    func,
    select,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    backref,
    declarative_base,
    joinedload,
    relationship,
    sessionmaker,
    validates,
)
from sqlalchemy.sql.expression import Select
from werkzeug.security import generate_password_hash


def _uri(app_name: str = "offstream") -> str:
    if uri := os.getenv("DATABASE_URL"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    else:
        app_dir = Path(get_app_dir(app_name, roaming=False, force_posix=True))
        app_dir.mkdir(exist_ok=True)
        path = app_dir / f"{app_name}.db"
        uri = f"sqlite:///{path}"
    return uri


_echo = os.getenv("FLASK_ENV") == "development"
engine = create_engine(_uri(), future=True, echo=_echo)

Session = sessionmaker(engine, future=True)

Base = declarative_base()


class Streamer(Base):
    __tablename__ = "streamers"

    _max_quality_re = re.compile(r"\d+p(\d+)?|[a-z_]+")
    _uri_template = "https://twitch.tv/{name}"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    max_quality = Column(String, default="best", nullable=False)

    @validates("name")  # type: ignore
    def validate_name(self, key: str, name: str) -> str:
        if not name:
            raise ValueError("Missing streamer name")
        return name.lower()

    @validates("max_quality")  # type: ignore
    def validate_quality(self, key: str, max_quality: str) -> str:
        if max_quality is not None and not re.fullmatch(
            self._max_quality_re, max_quality
        ):
            raise ValueError(f"Invalid max stream quality: {max_quality}")
        return max_quality

    @hybrid_property
    def url(self) -> str:
        return self._uri_template.format(name=self.name)


class Stream(Base):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True)
    streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=False)
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    streamer = relationship(
        Streamer, backref=backref("streams", cascade="all"), uselist=False
    )


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    ping_url = Column(String, nullable=True)
    ping_start_hour = Column(Integer, nullable=False, default=0)
    ping_end_hour = Column(Integer, nullable=False, default=24)

    @validates("ping_start_hour", "ping_end_hour")  # type: ignore
    def validate_hour(self, key: str, value: Optional[str]) -> Optional[int]:
        if value is None:
            return value
        try:
            hour = int(value)
        except ValueError as error:
            raise ValueError(f"Invalid hour: {value}") from error
        else:
            if 0 <= hour <= 24:
                return hour
        raise ValueError(f"Invalid hour: {value}")


def latest_streams(name: Optional[str] = None, limit: Optional[int] = None) -> Select:
    streams = (
        select(Stream)
        .options(joinedload(Stream.streamer))
        .order_by(Stream.created_at.desc())
        .limit(limit)
    )
    if name:
        streams = streams.join(Streamer).where(Streamer.name.contains(name))
    return streams


def settings(
    username: str = "offstream",
    passowrd_alphabet: str = string.ascii_lowercase,
    password_len: int = 9,
    ping_url: Optional[str] = None,
) -> tuple[Settings, str]:
    password = "".join(secrets.choice(passowrd_alphabet) for _ in range(password_len))
    settings_ = Settings(
        username=username, password=generate_password_hash(password), ping_url=ping_url
    )
    return settings_, password
