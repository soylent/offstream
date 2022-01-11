from concurrent.futures import Future
from unittest.mock import MagicMock, patch

import pytest
from offstream import db
from offstream.streaming import Recorder
from sqlalchemy import select


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


@pytest.fixture(autouse=True, scope="module")
def mock_ipfshttpclient():
    def _ipfs_add(*files, wrap_with_directory=False, **_kwargs):
        res = {"Hash": "fakecid", "Name": ""}
        return [res] * (len(files) + 1) if wrap_with_directory else res

    with patch("offstream.streaming.recorder.ipfshttpclient") as ipfshttpclient:
        ipfshttpclient.connect.return_value.add.side_effect = _ipfs_add
        yield


def test_start_with_one_streamer(streamer):
    with patch("offstream.streaming.recorder.Streamlink", autospec=True) as streamlink:
        sequence = MagicMock()
        sequence.segment.duration = 1.0
        response = MagicMock()
        response.iter_content.return_value = [b"x"]
        reader = MagicMock()
        reader.read.side_effect = lambda *args: reader.writer._write(sequence, response)
        stream = MagicMock()
        stream.open.return_value.__enter__.return_value = reader
        twitch = MagicMock()
        twitch_instance = twitch.return_value
        twitch_instance.streams.return_value.__getitem__.return_value = stream
        twitch_instance.get_title.return_value = "title"
        twitch_instance.get_category.return_value = "category"
        streamlink.return_value.resolve_url.return_value = (twitch, None)
        recorder = Recorder()
        recorder.start(loop=False)

    stream = streamer.streams[0]

    assert stream.url.startswith("https://")
    assert "fakecid" in stream.url
    assert stream.title == "title"
    assert stream.category == "category"


def test_start_with_no_streamers(setup_db, session):
    recorder = Recorder()
    recorder.start(loop=False)

    assert not session.scalars(select(db.Stream)).all()


def test_start_after_close(streamer):
    recorder = Recorder()
    recorder.close()
    recorder.start()

    assert not streamer.streams
