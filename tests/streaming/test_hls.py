import offstream.streaming.hls as hls


def test_playlist(m3u8):
    playlist = hls.Playlist(version=4, playlist_type="event")
    playlist.append(url="https://example.org/", duration=4.1009)
    playlist.write(m3u8)
    assert m3u8.read() == (
        "#EXTM3U\n"
        "#EXT-X-PLAYLIST-TYPE:EVENT\n"
        "#EXT-X-TARGETDURATION:5\n"
        "#EXT-X-VERSION:4\n"
        "#EXT-X-MEDIA-SEQUENCE:0\n"
        "#EXT-X-ENDLIST\n"
        "#EXTINF:4.101,\n"
        "https://example.org/\n"
    )


def test_empty_playlist(m3u8):
    playlist = hls.Playlist()
    playlist.write(m3u8)
    assert m3u8.read() == (
        "#EXTM3U\n"
        "#EXT-X-PLAYLIST-TYPE:VOD\n"
        "#EXT-X-TARGETDURATION:10\n"
        "#EXT-X-VERSION:3\n"
        "#EXT-X-MEDIA-SEQUENCE:0\n"
        "#EXT-X-ENDLIST\n"
    )
