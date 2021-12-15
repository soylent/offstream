import os
from sqlalchemy import create_engine, func, Column, String, Integer, ForeignKey, MetaData, DateTime
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.exc import IntegrityError


uri = os.environ["DATABASE_URL"]
uri = uri.replace("postgres://", "postgresql://", 1)
engine = create_engine(uri, echo=True)

Session = sessionmaker(bind=engine)

metadata = MetaData(bind=engine)

Base = declarative_base(engine, metadata)

# TODO: Indices

class Stream(Base):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True)
    stream_id = Column(ForeignKey("streams.id"))
    url = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    stream = relationship("Stream", backref="recordings")


# metadata.drop_all()
metadata.create_all()

def create_recording(stream_url, recording_url):
    stream = Stream(url=stream_url)
    with Session() as session:
        session.add(stream)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            stream = session.query(Stream).filter_by(url=stream_url).one()
        recording = Recording(url=recording_url, stream=stream)
        session.commit()
    return recording


def update_recording_url(recording, url):
    with Session() as session:
        recording.url = url
        session.add(recording)
        session.commit()


def latest_recording(stream_url):
    with Session() as session:
        return session.query(Recording).join(Stream).filter(Stream.url==stream_url).order_by(Recording.created_at.desc()).first()
