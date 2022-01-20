import math
from pathlib import Path
from typing import List, NamedTuple, Optional

# See rfc8216 and https://developer.apple.com/documentation/http_live_streaming


class _Segment(NamedTuple):
    url: str
    duration: float
    title: Optional[str]


class Playlist:
    def __init__(
        self,
        version: int = 3,
        playlist_type: Optional[str] = "vod",
    ) -> None:
        self.version = version
        self.playlist_type = playlist_type.upper() if playlist_type else None
        self.segments: List[_Segment] = []

    def append(self, url: str, duration: float, title: str = "") -> None:
        segment = _Segment(url, duration, title)
        self.segments.append(segment)

    def write(self, path: Path) -> None:
        target_duration = max(
            map(lambda s: math.ceil(s.duration), self.segments), default=10
        )
        with path.open(mode="w", encoding="utf-8") as m3u8:
            m3u8.write("#EXTM3U\n")
            if self.playlist_type is not None:
                m3u8.write(f"#EXT-X-PLAYLIST-TYPE:{self.playlist_type}\n")
            m3u8.write(f"#EXT-X-TARGETDURATION:{target_duration}\n")
            m3u8.write(f"#EXT-X-VERSION:{self.version}\n")
            m3u8.write("#EXT-X-MEDIA-SEQUENCE:0\n")
            # XXX: Ideally, we want the video player to reload the
            # playlist periodically:
            #   #EXT-X-PLAYLIST-TYPE:EVENT
            #   #EXT-X-START:TIME-OFFSET=0
            # But FFmpeg doesn't support the EXT-X-START tag, so I had
            # to change the above to:
            #   #EXT-X-PLAYLIST-TYPE:VOD
            #   #EXT-X-ENDLIST
            m3u8.write("#EXT-X-ENDLIST\n")
            for segment in self.segments:
                m3u8.write(f"#EXTINF:{segment.duration:.3f},{segment.title}\n")
                m3u8.write(f"{segment.url}\n")
