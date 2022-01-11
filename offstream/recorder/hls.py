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
        start_time_offset: Optional[float] = 0.0,
        playlist_type: Optional[str] = "event",
    ) -> None:
        self.version = version
        self.playlist_type = playlist_type.upper() if playlist_type else None
        self.start_time_offset = start_time_offset
        self.segments: List[_Segment] = []

    def append(self, url: str, duration: float, title: str = "") -> None:
        segment = _Segment(url, duration, title)
        self.segments.append(segment)

    def write(self, path: Path) -> None:
        target_duration = max(map(lambda s: s.duration, self.segments), default=0)
        with path.open(mode="w", encoding="utf-8") as m3u8:
            m3u8.write("#EXTM3U\n")
            m3u8.write(f"#EXT-X-VERSION:{self.version}\n")
            if self.playlist_type is not None:
                m3u8.write(f"#EXT-X-PLAYLIST-TYPE:{self.playlist_type}\n")
            # Many players don't support the EXT-X-START tag, so I added
            # EXT-X-ENDLIST as a workaround. Unfortunately, it prevents players
            # from reloading the playlist.
            m3u8.write("#EXT-X-ENDLIST\n")
            m3u8.write(f"#EXT-X-TARGETDURATION:{target_duration:.3f}\n")
            if self.start_time_offset is not None:
                m3u8.write(f"#EXT-X-START:TIME-OFFSET={self.start_time_offset:.3f}\n")
            for segment in self.segments:
                m3u8.write(f"#EXTINF:{segment.duration:.3f},{segment.title}\n")
                m3u8.write(f"{segment.url}\n")
