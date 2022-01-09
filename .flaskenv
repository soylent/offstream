# Development environment configuration
# Use a local SQLite database
DATABASE_URL=sqlite:///offstream.db
# Flask environment
FLASK_ENV=development
# Flush HLS segments to IPFS once their size exceeds 500K
OFFSTREAM_BUFFER_SIZE=500000
# Check each stream every 15 seconds
OFFSTREAM_CHECK_INTERVAL_SECONDS=20
# Listen port
PORT=5000
# Enable SQLAlchemy 2.0 deprecation mode
SQLALCHEMY_WARN_20=1
