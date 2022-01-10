import logging
import os
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from pathlib import Path
from queue import Queue
from tempfile import TemporaryDirectory
from types import TracebackType
from typing import NamedTuple, Optional, Any

import ipfshttpclient  # type: ignore
from offstream import db

from .hls import Playlist

IPFS_GATEWAY_URI_TEMPLATE = os.getenv(
    "OFFSTREAM_IPFS_GATEWAY_URI_TEMPLATE", "https://{cid}.ipfs.infura-ipfs.io/{path}"
)
# "https://gateway.ipfs.io/ipfs/{cid}/{path}"
IPFS_API_ADDR = os.getenv(
    "OFFSTREAM_IPFS_API_ADDR", "/dns/ipfs.infura.io/tcp/5001/https"
)


def _ipfs_url(cid: str, path: str = "") -> str:
    return IPFS_GATEWAY_URI_TEMPLATE.format(cid=cid, path=path)


class Segment(NamedTuple):
    file: str
    size: int
    duration: float


class RecordedStream:
    PLAYLIST_NAME = "playlist.m3u8"

    def __init__(
        self,
        queue: Queue[str],
        streamer_name: str,
        dirty_buffer_size: int,
    ) -> None:
        self._dirty_buffer_size = dirty_buffer_size
        self._dirty_segments: list[Segment] = []
        self._dirty_size = 0
        self._ipfs = ipfshttpclient.connect(addr=IPFS_API_ADDR, session=True)
        self._logger = logging.getLogger("offstream")
        self._playlist = Playlist()
        self._queue = queue
        self._streamer_name = streamer_name
        self._uploader = ThreadPoolExecutor(max_workers=1)
        self._workdir = TemporaryDirectory(prefix="offstream-")
        self.workdir_path = Path(self._workdir.name)

    def append_segment(self, file: str, size: int, duration: float) -> None:
        def upload_complete(future: Future[str]) -> None:
            try:
                stream_url = future.result()
                self._logger.debug("Flushed %s", self._streamer_name)
            except CancelledError:  # Closing time
                pass
            else:
                self._queue.put(stream_url)

        segment = Segment(file, size, duration)
        self._dirty_size += size
        self._dirty_segments.append(segment)
        if self._dirty_size > self._dirty_buffer_size:
            segments, self._dirty_segments = self._dirty_segments, []
            self._dirty_size = 0
            self._logger.info("Flushing %s", self._streamer_name)
            try:
                upload = self._uploader.submit(self._flush, segments)
            except RuntimeError:  # Closing time
                pass
            else:
                upload.add_done_callback(upload_complete)

    def _flush(self, segments: list[Segment]) -> str:
        files = [self.workdir_path / segment.file for segment in segments]
        ipfs_files = self._ipfs.add(
            *files, trickle=True, wrap_with_directory=True, cid_version=1
        )
        for file in files:
            os.remove(file)
        dir_ipfs = next(file for file in ipfs_files if not file["Name"])
        for segment in segments:
            url = _ipfs_url(dir_ipfs["Hash"], path=segment.file)
            self._playlist.append(url, segment.duration)
        m3u8 = self.workdir_path / self.PLAYLIST_NAME
        self._playlist.write(m3u8)
        m3u8_ipfs = self._ipfs.add(m3u8, cid_version=1)
        return _ipfs_url(m3u8_ipfs["Hash"])

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self._logger.debug("Closing %s", self._streamer_name, exc_info=True)
        # TODO: Flush dirty segments when the stream ends, but not on interrupt
        # or exception
        self._uploader.shutdown(wait=True, cancel_futures=True)
        self._ipfs.close()
        self._workdir.cleanup()

    def __enter__(self) -> "RecordedStream":
        return self
