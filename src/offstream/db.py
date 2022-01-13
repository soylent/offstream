import os
import re
import secrets
import string
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

_default_path = os.path.join(
    get_app_dir(app_name="offstream", roaming=False, force_posix=True), "offstream.db"
)
_uri = os.getenv("DATABASE_URL", f"sqlite://{_default_path}")
_uri = _uri.replace("postgres://", "postgresql://", 1)
_echo = os.getenv("FLASK_ENV") == "development"
engine = create_engine(_uri, future=True, echo=_echo)

Session = sessionmaker(engine, future=True)

Base = declarative_base()


class Streamer(Base):
    __tablename__ = "streamers"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    max_quality = Column(String, default="best", nullable=False)

    @validates("name")  # type: ignore
    def validate_name(self, key: str, name: str) -> str:
        if not name:
            raise ValueError("Missing streamer name")
        return name.lower()

    _MAX_QUALITY_RE = re.compile(r"\d+p(\d+)?|[a-z_]+")

    @validates("max_quality")  # type: ignore
    def validate_max_quality(self, key: str, max_quality: str) -> str:
        if max_quality is not None and not re.fullmatch(
            self._MAX_QUALITY_RE, max_quality
        ):
            raise ValueError(f"Invalid max stream quality: {max_quality}")
        return max_quality

    _URI_TEMPLATE = "https://twitch.tv/{name}"

    @hybrid_property
    def url(self) -> str:
        return self._URI_TEMPLATE.format(name=self.name)


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
    app_url = Column(String, nullable=False)


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


def streamers() -> Select:
    return select(Streamer)  # .where(Streamer.id == 6)


def streamer(name: str) -> Select:
    return select(Streamer).where(Streamer.name == name)


def settings(
    app_url: str,
    username: str = "offstream",
    passowrd_alphabet: str = string.ascii_lowercase,
    password_len: int = 9,
) -> tuple[Settings, str]:
    password = "".join(secrets.choice(passowrd_alphabet) for _ in range(password_len))
    settings_ = Settings(
        app_url=app_url, username=username, password=generate_password_hash(password)
    )
    return settings_, password
