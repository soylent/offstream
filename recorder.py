from tempfile import TemporaryDirectory
from pathlib import Path
from os.path import join
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor

from streamlink import Streamlink, StreamError
import ipfshttpclient

INFURA_GATEWAY_URL = "https://{cid}.ipfs.infura-ipfs.io/{path}"


def upload_to_ifps(segments, tempdir):
    infura_project_id = os.getenv("INFURA_PROJECT_ID")
    infura_project_secret = os.getenv("INFURA_PROJECT_SECRET")
    if infura_project_id and infura_project_secret:
        auth = (infura_project_id, infura_project_secret)
    else:
        auth = None
    with ipfshttpclient.connect(
        addr="/dns/ipfs.infura.io/tcp/5001/https",
        auth=None,
    ) as ipfs:
        files = [tempdir / name for name in segments]
        responses = ipfs.add(
            *files,
            trickle=True,
            wrap_with_directory=True,
            cid_version=1,
        )
        for i in range(len(responses)):
            response = responses[i]
            if not response["Name"]:
                cid = response["Hash"]
                del responses[i]
                break
        assert cid, "directory not found"

        m3u8name = tempdir / ".p.m3u8"
        if not os.path.exists(m3u8name):
            with open(m3u8name, "a") as m3u8:
                m3u8.write("#EXTM3U\n")
                m3u8.write("#EXT-X-VERSION:3\n")
                # TODO: Don't hardcode this
                m3u8.write("#EXT-X-TARGETDURATION:10\n")
                # TODO: What is this?
                # m3u8.write("#EXT-X-MEDIA-SEQUENCE:0")
        with open(m3u8name, "a") as m3u8:
            for response in responses:
                name = response["Name"]
                duration = segments[name]
                url = INFURA_GATEWAY_URL.format(cid=cid, path=name)
                m3u8.write(f"#EXTINF:{duration},\n{url}\n")
        for path in files:
            os.remove(path)
        final_m3u8name = tempdir / "p.m3u8"
        shutil.copyfile(m3u8name, final_m3u8name)
        with open(final_m3u8name, "a") as final_m3u8:
            final_m3u8.write("#EXT-X-ENDLIST\n")
        playlist_ipfs = ipfs.add(final_m3u8name, cid_version=1)
        return INFURA_GATEWAY_URL.format(cid=playlist_ipfs["Hash"], path="")


def record(reader):
    with TemporaryDirectory(prefix="offstream-") as tempdir, ThreadPoolExecutor(
        max_workers=1
    ) as executor:
        tempdir = Path(tempdir)
        segments = {}
        segsize = 0

        def process_sequence(sequence, response):
            nonlocal segsize, segments
            name = f"s{sequence.num}.ts"
            with open(tempdir / name, "wb") as ts:
                for chunk in response.iter_content(8192):
                    ts.write(chunk)
                    segsize += len(chunk)
            segments[name] = sequence.segment.duration
            # Infura: max request size is 100M
            if segsize > 2 * 2 ** 20:
                future = executor.submit(upload_to_ifps, segments, tempdir)
                future.add_done_callback(lambda fut: print(fut.result()))
                segsize = 0
                segments = {}

        reader.writer._write = process_sequence
        reader.writer.join()


def main():
    # TODO: accept command line options?
    name = "lirik"
    url = f"https://twitch.tv/{name}"
    quality = "720p60"

    streamlink = Streamlink()
    # We need to enable this option so that we can use response.raw
    streamlink.set_option("hls-segment-stream-data", True)
    streamlink.set_plugin_option("twitch", "disable_ads", True)
    streamlink.set_plugin_option("twitch", "disable_reruns", True)
    streamlink.set_plugin_option("twitch", "disable_hosting", True)

    while True:
        streams = streamlink.streams(url)
        if not streams:
            time.sleep(60 * 5)
            continue
        with streams[quality].open() as reader:
            record(reader)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
