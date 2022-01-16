
# Development

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
