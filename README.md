# offstream

Record your favorite twitch streams automatically and watch them later.

- There is no web UI, just use curl and your favorite video player.
- Streams are recorded as is, without re-transcoding.
- Recordings are never muted.
- Ads are optional.
- You can run it on Heroku (completely free) or on your own server.
- Recordings are stored on IPFS.
- RSS feed of all recordings is available. It can be consumed by youtube-dl,
  VLC, and other feed readers.
- Streams are available while the recording is in progress. The delay is small
  and configurable.
- This is a good option if you have slow Internet connection or old hardware.

## Installing

You can deploy the app to Heroku by clicking the button below and following the instructions.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

You can also install it locally.

TODO: If tty, then run offstream setup during the installation process.

```sh
$ pip install offstream
$ offstream setup
$ offstream
```

Either way, you will get credentials to control the app. Add them to your `~/.netrc` file (or `_netrc` on Windows).

```
machine your-app-name.herokuapp.com
    login offstream
    password <your-password>
```

## Usage

Next, add your favorite streamers.

```sh
$ curl https://your-app-name.herokuapp.com/streamers --netrc -d name=garybernhardt
$ curl https://your-app-name.herokuapp.com/streamers --netrc -d name=esl_sc2 -d max_quality=720p60
```

The `max_quality` parameter is optional and defaults to `best`. Typical stream
quality options are
`audio_only`, `160p`, `360p`, `480p`, `720p`, `720p60`, `1080p60`, `best`.

When any of the streamers goes live, the app will record the stream.

Finally, to watch the latest recording, open the following URL in mpv, VLC,
QuickTime, or any other video player.

```sh
$ mpv https://your-app-name.herokuapp.com/latest/esl_sc2
```

An RSS feed of all recordings is available at `https://your-app-name.herokuapp.com/rss`.

TODO: To download a stream
\$ ffmpeg -i https://your-app-name.herokuapp.com/latest/someone -c copy rec.mp4

## API

- `POST /streamers -d name=<name> -d max_quality=<quality>`

  Track a new streamer.

- `DELETE /streamers/<name>`

  Delete a streamer. WARNING: Deletes all associated streams too.

- `GET /lastest/<name>`

  Get the latest recorded stream.

- `POST /settings -d ping_start_hour=<hour> -d ping_end_hour=<hour>`

  Modify ping settings. On Heroku, offstream keeps itself awake 24/7 by pinging
  itself periodically. You can save some dyno hours by changing the
  `ping_start_hour` and `ping_end_hour` settings to let the app sleep when no
  one is streaming.

- `GET /rss`

  RSS feed of all recordings.

## Configuration

The following environment variables are supported.

- `DATABASE_URL`
- `OFFSTREAM_FLUSH_THRESHOLD`
- `OFFSTREAM_CHECK_INTERVAL_SECONDS`
- `OFFSTREAM_IPFS_API_ADDR`
- `OFFSTREAM_IPFS_GATEWAY_URI_TEMPLATE`
- `OFFSTREAM_MAX_CONCURRENT_RECORDERS`
- `TZ` Your preferred timezone, e.g. `America/New_York`. Please see https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List

## FAQ

TODO

- Q. keepalive request failed for 'https://bafybeie3v6lomkfti2b4zsa4yj35nypojllvjrzpbzyxhn5tkfoqaswmbm.ipfs.infura-ipfs.io/18846.ts'
