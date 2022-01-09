import logging
import os
import random
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from queue import Queue
from threading import Event, Lock, Thread
from typing import IO, Any, Optional

from offstream import db
from requests.exceptions import ChunkedEncodingError, ConnectionError
from streamlink import Streamlink  # type: ignore

from .storage import RecordedStream

CHECK_INTERVAL_SECONDS = int(os.getenv("OFFSTREAM_CHECK_INTERVAL_SECONDS", "120"))
MAX_WORKER_THREADS = int(os.getenv("OFFSTREAM_MAX_WORKER_THREADS", "8"))


def _buffer_size() -> int:
    dyno_ram = int(os.getenv("DYNO_RAM", "512")) * 2 ** 20
    max_upload_size = 80 * 2 ** 20
    default_buffer_size = min(max_upload_size, dyno_ram // MAX_WORKER_THREADS)
    return int(os.getenv("OFFSTREAM_BUFFER_SIZE", default_buffer_size))


BUFFER_SIZE = _buffer_size()


class StreamURLUpdater(Thread):
    def __init__(self, queue: Queue[Optional[db.Stream]]):
        super().__init__()
        self._queue = queue

    def run(self) -> None:
        with db.Session() as session:
            while True:
                if stream := self._queue.get():
                    session.merge(stream)
                    session.commit()
                else:
                    break


class Scheduler:
    def __init__(self) -> None:
        self._closed = Event()
        self._logger = logging.getLogger("offstream")
        self._readers: set[IO[bytes]] = set()
        self._recorder = ThreadPoolExecutor(max_workers=MAX_WORKER_THREADS)
        self._session = db.Session()
        self._streamlink = self._create_streamlink()
        self._queue: Queue[Optional[db.Stream]] = Queue()
        self._stream_url_updater = StreamURLUpdater(self._queue)
        self._lock = Lock()

    def start(self) -> None:
        def recording_complete(future: Future[None]) -> None:
            del recording[future]
            try:
                future.result()  # Log exception if any
            except CancelledError:
                pass

        self._stream_url_updater.start()
        recording: dict[Future[None], int] = {}
        while not self._closed.is_set():
            for streamer in self._session.scalars(db.streamers()):
                if streamer.id in recording.values():
                    continue
                self._logger.info("Checking %s", streamer.name)
                try:
                    future = self._recorder.submit(self._record_streamer, streamer)
                except RuntimeError:  # Closing time
                    break
                else:
                    recording[future] = streamer.id
                    future.add_done_callback(recording_complete)
            self._closed.wait(CHECK_INTERVAL_SECONDS)

    def close(self) -> None:
        self._logger.info("\nClosing, please wait")
        with self._lock:
            self._closed.set()
            for reader in self._readers:
                reader.close()
        self._recorder.shutdown(wait=True, cancel_futures=True)
        self._queue.put(None)
        self._stream_url_updater.join()
        self._session.close()

    def _create_streamlink(self) -> Streamlink:
        streamlink = Streamlink()
        # We need to enable this option so that we can use response.raw
        streamlink.set_option("hls-segment-stream-data", True)
        # TODO: ENV?
        streamlink.set_plugin_option("twitch", "disable_ads", True)
        streamlink.set_plugin_option("twitch", "disable_hosting", True)
        streamlink.set_plugin_option("twitch", "disable_reruns", True)
        return streamlink

    def _record_streamer(self, streamer: db.Streamer) -> None:
        def process_sequence(
            sequence: Any, response: Any, *_args: Any, **_kwargs: Any
        ) -> None:
            segfile = recorded_stream.workdir_path / f"{sequence.num}.ts"
            size = 0
            with segfile.open("wb") as seg:
                try:
                    # TODO: reader.writer.WRITE_CHUNK_SIZE not yet released
                    for chunk in response.iter_content(8192):
                        reader.buffer.write(chunk)
                        size += seg.write(chunk)
                except (ConnectionError, ChunkedEncodingError) as error:
                    print("!! Caught", error)
                    reader.close()
                    return
            recorded_stream.append_segment(
                segfile.name, size, sequence.segment.duration
            )

        assert streamer.id
        assert streamer.name
        plugin_class, url = self._streamlink.resolve_url(streamer.url)
        plugin = plugin_class(url)
        if streams := plugin.streams(sorting_excludes=[f">{streamer.max_quality}"]):
            stream = streams["best"]
            stream.force_restart = True
            with stream.open() as reader:
                with self._lock:
                    if self._closed.is_set():
                        return
                    self._readers.add(reader)
                try:
                    self._logger.info("Recording %s", streamer.name)
                    db_stream = db.Stream(
                        streamer=streamer,
                        category=plugin.get_category(),
                        title=plugin.get_title(),
                    )
                    with RecordedStream(
                        self._queue, db_stream, streamer.name, BUFFER_SIZE
                    ) as recorded_stream:
                        reader.writer._write = process_sequence  # HACK
                        while reader.read(-1):
                            pass
                finally:
                    with self._lock:
                        self._readers.remove(reader)
