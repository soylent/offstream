import offstream.recorder.hls as hls


def test_playlist(m3u8):
    playlist = hls.Playlist(version=4, start_time_offset=1.23, playlist_type="live")
    playlist.append(url="https://example.org/", duration=4.56)
    playlist.write(m3u8)
    assert m3u8.read() == (
        "#EXTM3U\n"
        "#EXT-X-VERSION:4\n"
        "#EXT-X-PLAYLIST-TYPE:LIVE\n"
        "#EXT-X-ENDLIST\n"
        "#EXT-X-TARGETDURATION:4.560\n"
        "#EXT-X-START:TIME-OFFSET=1.230\n"
        "#EXTINF:4.560,\n"
        "https://example.org/\n"
    )


def test_empty_playlist(m3u8):
    playlist = hls.Playlist()
    playlist.write(m3u8)
    assert m3u8.read() == (
        "#EXTM3U\n"
        "#EXT-X-VERSION:3\n"
        "#EXT-X-PLAYLIST-TYPE:EVENT\n"
        "#EXT-X-ENDLIST\n"
        "#EXT-X-TARGETDURATION:0.000\n"
        "#EXT-X-START:TIME-OFFSET=0.000\n"
    )
