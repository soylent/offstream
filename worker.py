from datetime import datetime
from zoneinfo import ZoneInfo
import shutil
import time

from streamlink import Streamlink, StreamError

name = "lirik"
url = f"https://twitch.tv/{name}"
quality = "best"

streamlink = Streamlink()
streamlink.set_plugin_option("twitch", "disable_ads", True)
streamlink.set_plugin_option("twitch", "disable_reruns", True)
streamlink.set_plugin_option("twitch", "disable_hosting", True)

while True:
    # Attempt to fetch streams
    try:
        streams = streamlink.streams(url)
    except NoPluginError:
        exit("Streamlink is unable to handle the URL '{0}'".format(url))
    except PluginError as err:
        exit("Plugin error: {0}".format(err))

    if not streams:
        time.sleep(60 * 5)
        continue

    # Look for specified stream
    if quality not in streams:
        exit("Unable to find '{0}' stream on URL '{1}'".format(quality, url))

    # We found the stream
    stream = streams[quality]

    try:
        with stream.open() as src:
            stream_ended = False
            chunk = 1
            while not stream_ended:
                now = datetime.now(tz=ZoneInfo("America/New_York"))
                filename = "{name}-{now:%Y}-{now:%m}-{now:%d}-{chunk:02d}".format(
                    name=name, now=now, chunk=chunk
                )
                with open(f"files/{filename}.mp4", "wb") as dst:
                    size = 0
                    while True:
                        buf = src.read(16 * 1024)
                        if not buf:
                            stream_ended = True
                            break
                        dst.write(buf)
                        size += len(buf)
                        if size >= 1024 * 1024 * 1024:
                            chunk += 1
                            break
    except StreamError as err:
        exit("Failed to open stream: {0}".format(err))
    except IOError as err:
        exit("Failed to read data from stream: {0}".format(err))
