# offstream

Record your favorite twitch streams automatically and watch them later.

- There is no web UI, just use curl and your favorite video player.
- Streams are recorded as is, without re-transcoding.
- Recordings are never muted.
- Ads are optional.
- You can run it on Heroku (completely free) or your own server.
- Recordings are stored on IPFS.
- RSS feed of all recordings is available. It can be consumed by youtube-dl,
  VLC, and other feed readers.
- Streams are available while the recording is in progress.

## Installing

### Heroku

You can deploy the app to Heroku by clicking the button below and following the
instructions. IMPORTANT: When the app is deployed, click on the "View" button at
the bottom to complete the setup.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

### Local installation

1. Install the package.
   ```sh
   $ pip install offstream
   ```
1. Setup your local sqlite database located at `~/.offstream/offstream.db`.
   ```sh
   $ offstream setup
   ```
   You will get credentials to control the app. I recommend adding them to your
   `~/.netrc` file (or `_netrc` on Windows).
   ```
   machine <your-app-hostname>
       login offstream
       password <your-password>
   ```
1. Start the app.
   ```sh
   $ offstream
   ```

## Usage

Next, add your favorite streamers.

```sh
$ curl https://your-app-name.herokuapp.com/streamers --netrc -d name=garybernhardt
$ curl https://your-app-name.herokuapp.com/streamers --netrc -d name=esl_sc2 -d max_quality=720p60
```

The `max_quality` parameter is optional and defaults to `best`. Typical stream
quality options are <br>
`audio_only`, `160p`, `360p`, `480p`, `720p`, `720p60`, `1080p60`, `best`.

When any of the streamers goes live, the app will record the stream.

Finally, to watch the latest recording, open the following URL in mpv, VLC,
QuickTime, or any other video player.

```sh
$ mpv https://your-app-name.herokuapp.com/latest/esl_sc2
```

An RSS feed of all recordings is available at `https://your-app-name.herokuapp.com/rss`.

## API

- `POST /streamers -d name=<name> -d max_quality=<quality>`

  Track a new streamer.

  Requires auth.

- `DELETE /streamers/{name}`

  Delete a streamer. WARNING: Deletes all associated recordings too.

  Requires auth.

- `GET /latest/{name}`

  Get the latest recorded stream.

- `POST /settings -d ping_start_hour=<hour> -d ping_end_hour=<hour>`

  Modify ping settings. On Heroku, offstream keeps itself awake 24/7 by pinging
  itself periodically. You can save some dyno hours by changing the
  `ping_start_hour` and `ping_end_hour` settings to let the app sleep when no
  one is streaming.

  Requires auth.

- `GET /rss`

  RSS feed of all recordings.

## Configuration

The following environment variables are supported.

- `OFFSTREAM_FLUSH_THRESHOLD`

  Default: automatically calculated, normally `100000000` bytes (100M).

- `OFFSTREAM_CHECK_INTERVAL`

  Default: `120` seconds

- `OFFSTREAM_IPFS_API_ADDR`

  Default: `/dns/ipfs.infura.io/tcp/5001/https`

- `OFFSTREAM_IPFS_GATEWAY_URI_TEMPLATE`

  Default: `https://{cid}.ipfs.infura-ipfs.io/{path}`

- `OFFSTREAM_MAX_CONCURRENT_RECORDERS`

  Default: `5`

- `DATABASE_URL`

  Default: `sqlite:///$HOME/.offstream/offstream.db`

- `TZ`

  Preferred timezone, e.g. `America/New_York`. Please see
  https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List

## FAQ

- Q: My video player reports the following error: `keepalive request failed for 'https://bafybeie3v6lomkfti2b4zsa4yj35nypojllvjrzpbzyxhn5tkfoqaswmbm.ipfs.infura-ipfs.io/18846.ts'`

  A: This warning can be safely ignored. It's because Infura keeps the root
  content identifier (CID) in a subdomain, rather than in the path portion of
  the URL.

## See Also

Please also check out the [streamlink](https://streamlink.github.io/) project.
