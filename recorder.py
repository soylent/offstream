import math
import os
import random
import shutil
import sys
import time
import queue
from concurrent.futures import ThreadPoolExecutor
import threading
from pathlib import Path
from tempfile import TemporaryDirectory

from streamlink import Streamlink, StreamError
import ipfshttpclient

INFURA_GATEWAY_URL = "https://{cid}.ipfs.infura-ipfs.io/{path}"


def upload_stream(segments, tempdir):
    print(f"Upload seq {threading.current_thread().name}")
    with ipfshttpclient.connect(
        addr="/dns/ipfs.infura.io/tcp/5001/https",
    ) as ipfs:
        m3u8_stub = tempdir / ".playlist.m3u8"
        if not os.path.exists(m3u8_stub):
            with open(m3u8_stub, "a") as m3u8_fd:
                m3u8_fd.write("#EXTM3U\n")
                m3u8_fd.write("#EXT-X-VERSION:3\n")
                # TODO: Better ideas?
                target_duration = max(map(math.ceil, segments.values()))
                m3u8_fd.write(f"#EXT-X-TARGETDURATION:{target_duration}\n")
        files = [tempdir / name for name in segments]
        ipfs_files = ipfs.add(
            *files,
            trickle=True,
            wrap_with_directory=True,
            cid_version=1,
        )
        ipfs_dir = next(f for f in ipfs_files if not f["Name"])
        with open(m3u8_stub, "a") as m3u8_fd:
            for name in segments:
                duration = segments[name]
                url = INFURA_GATEWAY_URL.format(cid=ipfs_dir["Hash"], path=name)
                m3u8_fd.write(f"#EXTINF:{duration},\n{url}\n")
        for path in files:
            os.remove(path)
        m3u8 = tempdir / "playlist.m3u8"
        shutil.copyfile(m3u8_stub, m3u8)
        with open(m3u8, "a") as m3u8_fd:
            m3u8_fd.write("#EXT-X-ENDLIST\n")
        m3u8_ipfs = ipfs.add(m3u8, cid_version=1)
        return INFURA_GATEWAY_URL.format(cid=m3u8_ipfs["Hash"], path="")


def record(url, quality):
    print(f"Recording {url} {threading.current_thread().name}")
    streamlink = Streamlink()
    # We need to enable this option so that we can use response.raw
    streamlink.set_option("hls-segment-stream-data", True)
    # Threads to download HLS segments
    streamlink.set_option("hls-segment-threads", 2)
    # Skip as far back as possible
    streamlink.set_option("hls-live-restart", True)
    streamlink.set_option("default-stream", "720p60,720p,best")
    streamlink.set_plugin_option("twitch", "disable_ads", True)
    streamlink.set_plugin_option("twitch", "disable_reruns", True)
    streamlink.set_plugin_option("twitch", "disable_hosting", True)

    def process_sequence(sequence, response, is_map):
        print(f"Process seq {threading.current_thread().name}")
        nonlocal segsize, segments
        segname = f"segment{sequence.num}.ts"
        with open(tempdir / segname, "wb") as ts:
            for chunk in response.iter_content(8192):
                ts.write(chunk)
                segsize += len(chunk)
        segments[segname] = sequence.segment.duration
        # Infura: max request size is 100M
        # Heroku memory limit is 512M
        if segsize > 40 * 2 ** 20:
            future = uploader.submit(upload_stream, segments, tempdir)
            future.add_done_callback(lambda fut: print(url, fut.result()))
            segsize = 0
            segments = {}

    with TemporaryDirectory(prefix="offstream-") as tempdir, ThreadPoolExecutor(
        thread_name_prefix="Thread-StreamUploader", max_workers=1
    ) as uploader:
        tempdir = Path(tempdir)
        segments = {}
        segsize = 0
        if streams := streamlink.streams(url):
            with streams[quality].open() as reader:
                reader.writer._write = process_sequence
                reader.writer.join()
    print(f"Done {url} {threading.current_thread().name}")
    # Random sleep time to avoid activity spikes
    time.sleep(random.randint(1, 60) + 4 * 60)


if __name__ == "__main__":
    q = queue.Queue()

    q.put(("https://twitch.tv/georgehotz", "best"))
    q.put(("https://twitch.tv/garybernhardt", "best"))
    q.put(("https://twitch.tv/lirik", "720p60"))
    q.put(("https://twitch.tv/nl_kripp", "best"))

    recorder = ThreadPoolExecutor(
        max_workers=8, thread_name_prefix="Thread-StreamRecorder"
    )
    try:
        while True:
            stream = q.get()
            print(f"Submitting seq {threading.current_thread().name}")
            future = recorder.submit(record, *stream)
            future.add_done_callback(
                lambda fut, stream=stream: fut.exception() or q.put(stream)
            )
    finally:
        recorder.shutdown(wait=False, cancel_futures=True)
