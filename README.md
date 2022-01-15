# offstream

Record your favorite twitch streams automatically and watch them later.

- There is no web UI, just use curl and your favorite video player.
- Streams are recorded as is, without re-transcoding.
- Recordings are never muted.
- Ads are optional.
- Completely free. You can deploy it to Heroku or run it on your own server.
- Recordings are stored on IPFS.
- RSS feed of all recordings is available. It can be consumed by youtube-dl,
  VLC, and other feed readers.
- TODO: No playback performance issues
- Streams are available while the recording is in progress. The delay is small
  and configurable.
- This is a good option if you have slow or unreliable Internet connection.

## Installing

To deploy the app, click the button below and follow the instructions.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

Once the app is ready, you will get your credentials to control the app. Add
them to your `~/.netrc` file (or `_netrc` on Windows).

```
machine your-app-name.herokuapp.com
    login offstream
    password <your-password>
```

Next, add your favorite streamers.

```sh
$ curl https://your-app-name.herokuapp.com/streamers --netrc -d name=garybernhardt
$ curl https://your-app-name.herokuapp.com/streamers --netrc -d name=esl_sc2 -d max_quality=720p60
```

Typical stream quality options are
`audio_only`, `160p`, `360p`, `480p`, `720p`, `720p60`, `1080p60`, `best`.

When any of the streamers is live, the app will record the stream.

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
  Delete the streamer. WARNING: Deletes associated streams too.
- `GET /lastest/<name>`
  Watch the latest stream.
- `GET /rss`
  Feed of recordings.

## Configuration

The following environment variables are supported.

- `OFFSTREAM_AWAKE_END_HOUR`
- `OFFSTREAM_AWAKE_START_HOUR`
- `OFFSTREAM_FLUSH_THRESHOLD`
- `OFFSTREAM_CHECK_INTERVAL_SECONDS`
- `OFFSTREAM_IPFS_API_ADDR`
- `OFFSTREAM_IPFS_GATEWAY_URI_TEMPLATE`
- `OFFSTREAM_MAX_CONCURRENT_RECORDERS`
- `TZ` Your preferred timezone, e.g. `America/New_York`. Please see https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List

## FAQ

TODO

- Q. keepalive request failed for 'https://bafybeie3v6lomkfti2b4zsa4yj35nypojllvjrzpbzyxhn5tkfoqaswmbm.ipfs.infura-ipfs.io/18846.ts'

## Development

1. Create a virtual environment and activate it.
   ```sh
   python -m venv venv
   source venv/bin/activate
   ```
1. Install dependencies.
   ```sh
   pip install -e .[test]
   ```
1. Run tests.
   ```sh
   pytest
   ```
1. Setup a local SQLite database.
   ```sh
   flask offstream setup
   ```
1. Start the app.
   ```sh
   flask offstream
   ```

## Flask commands

This app has a few custom flask commands.

```sh
$ flask offstream --help
```

| command                  | description                    |
| ------------------------ | ------------------------------ |
| `flask run`              | Start API.                     |
| `flask offstream`        | Start API and stream recorder. |
| `flask offstream record` | Start stream recorder.         |
| `flask offstream create` | Create db tables.              |
| `flask offstream setup`  | Setup the database.            |
| `flask offstream ping`   | Ping itself to prevent idling. |
