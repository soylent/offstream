import os
import signal
import subprocess
import time
import sys

while True:
    try:
        ytdl = subprocess.Popen(
            [
                "youtube-dl",
                "--ffmpeg-location",
                "bin",
                "--output",
                "files/%(title)s-%(id)s.%(ext)s",
                "https://twitch.tv/shroud",
            ],
            preexec_fn=os.setsid,
        )
        ytdl.wait(2 * 60)  # Must be at least a minute
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
        # Make a cut
        os.killpg(ytdl.pid, signal.SIGINT)
        ytdl.wait()
        if isinstance(error, KeyboardInterrupt):
            sys.exit(ytdl.returncode)
    else:
        # Stream is offline or youtube-dl failed
        time.sleep(10 * 60)
