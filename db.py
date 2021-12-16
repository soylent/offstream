import os
from sqlalchemy import create_engine, func, Column, String, Integer, ForeignKey, MetaData, DateTime
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.exc import IntegrityError


uri = os.environ["DATABASE_URL"]
uri = uri.replace("postgres://", "postgresql://", 1)
engine = create_engine(uri, echo=False)

Session = sessionmaker(bind=engine)

metadata = MetaData(bind=engine)

Base = declarative_base(engine, metadata)

# TODO: Indices

class Streamer(Base):
    __tablename__ = "streamers"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)


class Stream(Base):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True)
    streamer_id = Column(ForeignKey("streamers.id"))
    url = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    streamer = relationship("Streamer", backref="streams")


metadata.create_all()

def create_stream(streamer_url, stream_url):
    streamer = Streamer(url=streamer_url)
    with Session() as session:
        session.add(streamer)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            streamer = session.query(Streamer).filter_by(url=streamer_url).one()
        stream = Stream(url=stream_url, streamer=streamer)
        session.commit()
    return stream


def update_stream_url(stream, url):
    with Session() as session:
        stream.url = url
        session.add(stream)
        session.commit()


def latest_stream(name):
    with Session() as session:
        return session.query(Stream).join(Streamer).filter(Streamer.url.ilike(f"%{name}%")).order_by(Stream.created_at.desc()).first()
