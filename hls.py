import math
from typing import IO, List, NamedTuple, Optional

# See rfc8216 and https://developer.apple.com/documentation/http_live_streaming


class Segment(NamedTuple):
    url: str
    duration: float
    title: Optional[str]


class Playlist:
    def __init__(
        self,
        version: int = 3,
        start_time_offset: Optional[float] = 0.0,
        playlist_type: Optional[str] = "event",
    ):
        self.version = version
        self.playlist_type = playlist_type.upper() if playlist_type else None
        self.start_time_offset = start_time_offset
        self.segments: List[Segment] = []

    def append_segment(self, url: str, duration: float, title: Optional[str] = None):
        segment = Segment(url, duration, title)

        self.segments.append(segment)

    def write(self, path: str):
        target_duration = max(map(lambda s: math.ceil(s.duration), self.segments))
        with open(path, "w") as fd:
            fd.write("#EXTM3U\n")
            fd.write("#EXT-X-VERSION:{}\n".format(self.version))
            if self.playlist_type is not None:
                fd.write("#EXT-X-PLAYLIST-TYPE:{}\n".format(self.playlist_type))
            # No more segments will be added to the playlist file.
            # NOTE: Many players don't support the EXT-X-START tag, so I added
            # this tag as a workaround. Unfortunately, this also prevents
            # players from reloading the playlist.
            fd.write("#EXT-X-ENDLIST\n")
            # The maximum segment duration
            fd.write("#EXT-X-TARGETDURATION:{:.3f}\n".format(target_duration))
            if self.start_time_offset is not None:
                # Time offset from the beginning of the playlist
                fd.write(
                    "#EXT-X-START:TIME-OFFSET={:.1f}\n".format(self.start_time_offset)
                )
            for segment in self.segments:
                fd.write("#EXTINF:{:.3f}\n{}\n".format(segment.duration, segment.url))
