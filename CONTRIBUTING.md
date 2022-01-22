# Contributing

offstream is a single-process multi-threaded app that consists of two
independent parts:

1. Flask **API** that is served by a simple HTTP server running in a dedicated
   thread.
1. Stream **recorder** that has a main thread which submits recording jobs to a
   thread pool executor. Each worker thread accumulates stream segments until
   the total size reaches the flush threshold. Then it generates an HLS playlist
   and uploads the segments and the playlist to IPFS. When the upload is
   complete, the URL of the playlist is added to the database.

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
1. Setup a local SQLite database. Add the credentials to your `~/.netrc` file.
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

| command                   | description                    |
| ------------------------- | ------------------------------ |
| `flask run`               | Start only API.                |
| `flask offstream`         | Start API and stream recorder. |
| `flask offstream record`  | Start only stream recorder.    |
| `flask offstream init-db` | Create db tables.              |
| `flask offstream setup`   | Setup the database.            |
| `flask offstream ping`    | Ping itself to prevent idling. |
