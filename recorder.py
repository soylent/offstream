import os
import queue
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

import ipfshttpclient
from streamlink import Streamlink

from db import create_stream, streamers, update_stream_url
from hls import Playlist

INFURA_GATEWAY_URL = "https://{cid}.ipfs.infura-ipfs.io/{path}"
# "https://gateway.ipfs.io/ipfs/{cid}/{path}"
WORKER_THREADS = 8

streamlink = Streamlink()
# We need to enable this option so that we can use response.raw
streamlink.set_option("hls-segment-stream-data", True)
# Threads to download HLS segments
streamlink.set_option("hls-segment-threads", 2)
# Skip as far back as possible
streamlink.set_option("hls-live-restart", True)
streamlink.set_plugin_option("twitch", "disable_ads", True)
streamlink.set_plugin_option("twitch", "disable_reruns", True)
streamlink.set_plugin_option("twitch", "disable_hosting", True)


class Recorder:
    def __init__(self, url: str, quality: str):
        self.stream = None
        self.playlist = Playlist()


def record(streamer):
    stream = None
    playlist = Playlist()

    def update_stream(stream_url):
        nonlocal stream
        if stream is None:
            stream = create_stream(streamer.url, stream_url)
        else:
            update_stream_url(stream, stream_url)

    def process_sequence(sequence, response, is_map):
        nonlocal segsize, segments
        segname = f"segment{sequence.num}.ts"
        with open(tempdir / segname, "wb") as ts:
            for chunk in response.iter_content(8192):  # WRITE_CHUNK_SIZE
                ts.write(chunk)
                segsize += len(chunk)
        segments[segname] = sequence.segment.duration
        # Infura: max request size is 100M
        # Heroku: memory limit is 512M
        stream_buffer_size = int(
            os.getenv(
                "OFFSTREAM_BUFFER_SIZE",
                min(80 * 2 ** 20, 512 * 2 ** 20 // WORKER_THREADS),
            )
        )
        if segsize > stream_buffer_size:
            future = uploader.submit(upload_stream, playlist, segments, tempdir)
            future.add_done_callback(lambda fut: update_stream(fut.result()))
            segsize = 0
            segments = {}

    with TemporaryDirectory(prefix="offstream-") as tempdir, ThreadPoolExecutor(
        thread_name_prefix="Thread-StreamUploader", max_workers=1
    ) as uploader:
        tempdir = Path(tempdir)
        segments = {}
        segsize = 0
        if streams := streamlink.streams(streamer.url):
            with streams[streamer.quality].open() as reader:
                reader.writer._write = process_sequence
                reader.writer.join()
    # Random sleep time to avoid activity spikes
    time.sleep(random.randint(1, 60) + 4 * 60)


def upload_stream(playlist, segments, tempdir):
    files = [tempdir / name for name in segments]
    with ipfshttpclient.connect(
        addr="/dns/ipfs.infura.io/tcp/5001/https",
    ) as ipfs:
        ipfs_files = ipfs.add(
            *files,
            trickle=True,
            wrap_with_directory=True,
            cid_version=1,
        )
        ipfs_dir = next(f for f in ipfs_files if not f["Name"])
        for path in files:
            os.remove(path)
        for name in segments:
            duration = segments[name]
            url = INFURA_GATEWAY_URL.format(cid=ipfs_dir["Hash"], path=name)
            playlist.append_segment(url, duration)
        m3u8 = tempdir / "playlist.m3u8"
        playlist.write(m3u8)
        m3u8_ipfs = ipfs.add(m3u8, cid_version=1)
        return INFURA_GATEWAY_URL.format(cid=m3u8_ipfs["Hash"], path="")


if __name__ == "__main__":
    q = queue.Queue()

    for streamer in streamers():
        q.put(streamer)

    recorder = ThreadPoolExecutor(
        max_workers=WORKER_THREADS, thread_name_prefix="Thread-StreamRecorder"
    )
    try:
        while True:
            streamer = q.get()
            future = recorder.submit(record, streamer)
            future.add_done_callback(
                lambda fut, streamer=streamer: fut.exception() or q.put(streamer)
            )
    finally:
        recorder.shutdown(wait=False, cancel_futures=True)
