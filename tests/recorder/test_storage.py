from queue import Queue
from typing import Optional
from unittest.mock import patch

import pytest
from offstream import db
from offstream.recorder.storage import RecordedStream


@pytest.fixture(autouse=True, scope="module")
def mock_ipfshttpclient():
    def ipfs_add(*files, wrap_with_directory=False, **_kwargs):
        res = {"Hash": "fakecid", "Name": ""}
        return [res] * (len(files) + 1) if wrap_with_directory else res

    with patch("offstream.recorder.storage.ipfshttpclient") as ipfshttpclient:
        ipfshttpclient.connect.return_value.add.side_effect = ipfs_add
        yield


def test_recorded_stream_flushing(stream):
    queue: Queue[Optional[db.Stream]] = Queue()
    with RecordedStream(
        queue, stream, stream.streamer.name, dirty_buffer_size=1
    ) as recorded_stream:
        for segnum in range(2):
            segment = recorded_stream.workdir_path / f"{segnum}.ts"
            size = segment.write_bytes(b"x")
            recorded_stream.append_segment(segment.name, size, duration=1.0)
            if segnum == 0:
                assert queue.empty()
            else:
                returned_stream = queue.get(timeout=1)
                assert stream == returned_stream
                assert "fakecid" in stream.url
