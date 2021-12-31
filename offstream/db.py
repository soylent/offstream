import os
import re
import secrets
import string
from typing import Optional

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
    declarative_base,
    joinedload,
    relationship,
    sessionmaker,
    backref,
    validates,
)
from sqlalchemy.sql.expression import Select
from werkzeug.security import generate_password_hash

uri = os.environ["DATABASE_URL"].replace("postgres://", "postgresql://", 1)
engine = create_engine(uri, future=True)

Session = sessionmaker(engine, future=True)

Base = declarative_base()


class Streamer(Base):
    __tablename__ = "streamers"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    quality = Column(String, default="best", nullable=False)

    @validates("name")  # type: ignore
    def validate_name(self, key: str, name: str) -> str:
        if not name:
            raise ValueError("Missing streamer name")
        return name.lower()

    _QUALITY_RE = re.compile(r"\d+p(\d+)?|[a-z_]+")

    @validates("quality")  # type: ignore
    def validate_quality(self, key: str, quality: str) -> str:
        if quality is not None and not re.fullmatch(self._QUALITY_RE, quality):
            raise ValueError(f"Invalid stream quality: {quality}")
        return quality

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

    streamer = relationship(Streamer, backref=backref("streams", cascade="all"), uselist=False)


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
    return select(Streamer)


def streamer(name: str) -> Select:
    return select(Streamer).where(Streamer.name == name)


def settings(
    app_url: str,
    username: str = "offstream",
    passowrd_alphabet: str = string.ascii_lowercase,
    password_len: int = 9,
) -> tuple[Settings, str]:
    password = "".join(secrets.choice(passowrd_alphabet) for _ in range(password_len))
    settings_ = Settings(app_url=app_url, username=username, password=generate_password_hash(password))
    return settings_, password
