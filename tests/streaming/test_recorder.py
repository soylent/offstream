from concurrent.futures import Future
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from requests.models import Response
from sqlalchemy import select
from streamlink.plugins.twitch import Twitch, TwitchHLSStream, TwitchHLSStreamReader
from streamlink.stream.hls import Sequence

from offstream import db
from offstream.streaming import Recorder


@pytest.fixture(autouse=True, scope="module")
def inline_thread_pool_executor():
    def _execute_inline(func, *args):
        result = func(*args)
        future = Future()
        future.set_result(result)
        return future

    with patch("offstream.streaming.recorder.ThreadPoolExecutor", autospec=True) as tpe:
        tpe.return_value.submit.side_effect = _execute_inline
        yield


@pytest.fixture(scope="module")
def ipfs_add():
    def _ipfs_add(*files, wrap_with_directory=False, **_kwargs):
        num = len(files) + 1 if wrap_with_directory else len(files)
        return [res] * num if num > 1 else res

    res = {"Hash": "fakecid", "Name": ""}
    with patch("offstream.streaming.recorder.ipfshttpclient") as ipfshttpclient:
        ipfshttpclient.connect.return_value.add.side_effect = _ipfs_add
        yield res


@pytest.fixture(scope="module")
def twitch():
    with patch("offstream.streaming.recorder.Streamlink", autospec=True) as streamlink:
        sequence = create_autospec(Sequence, instance=True, spec_set=True)
        sequence.segment.duration = 1.0
        response = create_autospec(Response, instance=True, spec_set=True)
        response.iter_content.return_value = [b"x"]
        reader = MagicMock()
        reader.read.side_effect = lambda *args: reader.writer._write(sequence, response)
        stream = create_autospec(TwitchHLSStream, instance=True)
        stream.open.return_value.__enter__.return_value = reader
        twitch_class = create_autospec(Twitch, spec_set=True)
        twitch_ = twitch_class.return_value
        twitch_.streams.return_value.__getitem__.return_value = stream
        twitch_.get_title.return_value = "title"
        twitch_.get_category.return_value = "category"
        streamlink.return_value.resolve_url.return_value = (twitch_class, None)
        yield twitch_


def test_start_with_one_streamer(streamer, twitch, ipfs_add):
    recorder = Recorder()
    recorder.start(_loop=False)

    stream = streamer.streams[0]

    assert stream.url.startswith("https://")
    assert ipfs_add["Hash"] in stream.url
    assert stream.title == twitch.get_title()
    assert stream.category == twitch.get_category()


def test_start_with_non_existent_streamer(streamer, twitch, session):
    twitch.streams.return_value = {}

    recorder = Recorder()
    recorder.start(_loop=False)

    assert not session.scalars(select(db.Stream)).all()


def test_start_with_no_acceptable_streams(streamer, twitch, session):
    twitch.streams.return_value = {
        "best-unfiltered": create_autospec(TwitchHLSStream, spec_set=True)
    }

    recorder = Recorder()
    recorder.start(_loop=False)

    assert not session.scalars(select(db.Stream)).all()


def test_start_with_no_streamers(setup_db, session):
    recorder = Recorder()
    recorder.start(_loop=False)

    assert not session.scalars(select(db.Stream)).all()


def test_start_after_close(streamer):
    recorder = Recorder()
    recorder.close()
    recorder.start()

    assert not streamer.streams
