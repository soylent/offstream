import logging
import os
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Lock
from types import TracebackType
from typing import IO, Any, NamedTuple, Optional

import ipfshttpclient  # type: ignore
from requests.exceptions import ChunkedEncodingError, ConnectionError
from sqlalchemy import select
from streamlink import Streamlink  # type: ignore

from offstream import db

from .hls import Playlist

# HACK: Suppress a version mismatch warning.
# This can be removed once ipfshttpclient is updated.
# We can't use warnings.catch_warnings() because it is not thread-safe.
ipfshttpclient.client.assert_version = lambda *args: True

MAX_CONCURRENT_RECORDERS = int(os.getenv("OFFSTREAM_MAX_CONCURRENT_RECORDERS", "5"))

_logger = logging.getLogger("offstream")


class Recorder:
    check_interval = int(os.getenv("OFFSTREAM_CHECK_INTERVAL", "120"))

    def __init__(self) -> None:
        self._closed = Event()
        self._executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_RECORDERS)
        self._lock = Lock()
        self._recording: dict[int, Optional[_Worker]] = {}
        self._session = db.Session()
        self._streamlink = self._create_streamlink()

    def start(self, _loop: bool = True) -> None:
        def _recording_complete(future: Future[None]) -> None:
            try:
                future.result()
            except CancelledError:  # Closing time
                _logger.info("Canceled recording")
            except Exception:
                _logger.warning("Exception while recording", exc_info=True)

        while not self._closed.is_set():
            for streamer in self._session.scalars(select(db.Streamer)):
                with self._lock:
                    if streamer.id in self._recording:
                        continue
                    self._recording[streamer.id] = None
                _logger.info("Checking %s", streamer.name)
                try:
                    future = self._executor.submit(self._record_streamer, streamer)
                except RuntimeError:  # Closing time
                    break
                else:
                    future.add_done_callback(_recording_complete)
            if not _loop:
                break
            self._closed.wait(self.check_interval)

    def close(self) -> None:
        _logger.info("\nClosing, please wait")
        with self._lock:
            self._closed.set()
            _logger.info("Closing %d stream reader(s)", len(self._recording))
            for worker in self._recording.values():
                if worker is not None:
                    worker.close()
        _logger.info("Shutting down executor")
        self._executor.shutdown(cancel_futures=True)
        self._session.close()

    def _create_streamlink(self) -> Streamlink:
        streamlink = Streamlink()
        # This option is on so that we can access segment chunks.
        streamlink.set_option("hls-segment-stream-data", True)
        streamlink.set_plugin_option("twitch", "disable_ads", True)
        streamlink.set_plugin_option("twitch", "disable_hosting", True)
        streamlink.set_plugin_option("twitch", "disable_reruns", True)
        return streamlink

    def _record_streamer(self, streamer: db.Streamer) -> None:
        assert streamer.id
        with _Worker(self._streamlink, streamer) as worker:
            with self._lock:
                if self._closed.is_set():
                    return
                assert self._recording[streamer.id] is None
                self._recording[streamer.id] = worker
            try:
                worker.start()
            finally:
                with self._lock:
                    del self._recording[streamer.id]


class _Segment(NamedTuple):
    file: str
    size: int
    duration: float


class _Worker:
    ipfs_request_size_limit = 10 ** 8  # 100M
    ipfs_api_addr = os.getenv(
        "OFFSTREAM_IPFS_API_ADDR",
        "/dns/ipfs.infura.io/tcp/5001/https",
    )
    ipfs_gateway_uri_template = os.getenv(
        "OFFSTREAM_IPFS_GATEWAY_URI_TEMPLATE",
        "https://{cid}.ipfs.infura-ipfs.io/{path}",
    )

    def __init__(self, streamlink: Streamlink, streamer: db.Streamer) -> None:
        self._closed = False
        self._dirty_segments: list[_Segment] = []
        self._dirty_size = 0
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._flush_threshold = self._calculate_flush_threshold()
        self._ipfs = ipfshttpclient.connect(addr=self.ipfs_api_addr, session=True)
        self._lock = Lock()
        self._playlist = Playlist()
        self._reader: Optional[IO[bytes]] = None
        self._session = db.Session()
        self._stream: Optional[db.Stream] = None
        self._streamer = streamer
        self._streamlink = streamlink
        self._workdir = TemporaryDirectory(prefix="offstream-")
        self._workdir_path = Path(self._workdir.name)

    def _calculate_flush_threshold(self) -> int:
        dyno_ram_size = int(os.getenv("DYNO_RAM", "512")) * 10 ** 6
        default_size = min(
            self.ipfs_request_size_limit, dyno_ram_size // MAX_CONCURRENT_RECORDERS
        )
        return int(os.getenv("OFFSTREAM_FLUSH_THRESHOLD", default_size))

    def start(self) -> None:
        def _process_sequence(
            sequence: Any, response: Any, *_args: Any, **_kwargs: Any
        ) -> None:
            size = 0
            segfile = self._workdir_path / f"{sequence.num}.ts"
            with segfile.open(mode="wb") as seg:
                try:
                    # TODO: Change to reader.writer.WRITE_CHUNK_SIZE
                    # when a new version of streamlink is released.
                    for chunk in response.iter_content(8192):
                        reader.buffer.write(chunk)
                        size += seg.write(chunk)
                except (ConnectionError, ChunkedEncodingError) as error:
                    _logger.warning(
                        "Exception while reading %s: %s", self._streamer.name, error
                    )
                    reader.close()
                    return
            self._append_segment(segfile.name, size, sequence.segment.duration)

        plugin_class, url = self._streamlink.resolve_url(self._streamer.url)
        plugin = plugin_class(url)
        # TODO: Handle PluginError?
        if streams := plugin.streams(
            sorting_excludes=[f">{self._streamer.max_quality}"]
        ):
            try:
                stream = streams["best"]
            except KeyError:
                _logger.warning(
                    "No %s streams with max quality %s found",
                    self._streamer.name,
                    self._streamer.max_quality,
                )
                return
            stream.force_restart = True
            with stream.open() as reader:
                with self._lock:
                    if self._closed:
                        return
                    self._reader = reader
                _logger.info("Recording %s", self._streamer.name)
                self._stream = db.Stream(
                    streamer_id=self._streamer.id,
                    category=plugin.get_category(),
                    title=plugin.get_title(),
                )
                self._session.add(self._stream)
                reader.writer._write = _process_sequence  # HACK
                try:
                    while reader.read(-1):
                        pass
                except OSError as error:
                    _logger.warning(
                        "Exception while recording %s: %s", self._streamer.name, error
                    )

    def _append_segment(self, file: str, size: int, duration: float) -> None:
        # When the threshold is large enough we do not want to exceed it.
        if self._dirty_size > 0 and self._dirty_size + size > self._flush_threshold:
            self._flush()
        segment = _Segment(file, size, duration)
        self._dirty_size += size
        self._dirty_segments.append(segment)
        # When the threshold is too small we will exceed it.
        if self._dirty_size > self._flush_threshold:
            self._flush()

    def _flush(self) -> None:
        def _upload_complete(future: Future[str]) -> None:
            try:
                assert self._stream
                self._stream.url = future.result()
                self._session.commit()
            except CancelledError:  # Closing time
                _logger.info("Canceled flushing %s", self._streamer.name)
            except Exception:
                # The recording will be playable, but it will miss a chunk.
                _logger.warning(
                    "Exception while flushing %s", self._streamer.name, exc_info=True
                )
            else:
                _logger.info("Flushed %s", self._streamer.name)

        _logger.info("Flushing %s", self._streamer.name)
        segments, self._dirty_segments = self._dirty_segments, []
        self._dirty_size = 0
        try:
            upload = self._executor.submit(self._upload_segments, segments)
        except RuntimeError:  # Closing time
            pass
        else:
            upload.add_done_callback(_upload_complete)

    def _upload_segments(self, segments: list[_Segment]) -> str:
        files = [self._workdir_path / segment.file for segment in segments]
        try:
            ipfs_files = self._ipfs.add(
                *files, trickle=True, wrap_with_directory=True, cid_version=1
            )
        finally:
            for file in files:
                os.remove(file)
        dir_ipfs = next(file for file in ipfs_files if not file["Name"])
        for segment in segments:
            url = self._ipfs_url(dir_ipfs["Hash"], path=segment.file)
            self._playlist.append(url, segment.duration)
        m3u8 = self._workdir_path / f"{self._streamer.name}.m3u8"
        self._playlist.write(m3u8)
        m3u8_ipfs = self._ipfs.add(m3u8, cid_version=1)
        return self._ipfs_url(m3u8_ipfs["Hash"])

    def _ipfs_url(self, cid: str, path: str = "") -> str:
        return self.ipfs_gateway_uri_template.format(cid=cid, path=path)

    def close(self) -> None:
        self._ipfs.close()
        with self._lock:
            self._closed = True
            if self._reader:
                _logger.info("Closing %s", self._streamer.name)
                self._reader.close()
                self._reader = None

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if not self._closed and self._dirty_size > 0:
            self._flush()
        cancel_futures = self._closed
        self.close()
        self._executor.shutdown(cancel_futures=cancel_futures)
        self._session.close()
        self._workdir.cleanup()

    def __enter__(self) -> "_Worker":
        return self
