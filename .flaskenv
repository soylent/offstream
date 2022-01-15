# Development environment configuration
#
# Use a local SQLite database
DATABASE_URL=sqlite:///offstream.db
# Flask app
FLASK_APP=offstream.app
# Flask environment
FLASK_ENV=development
# Flush buffered HLS segments to IPFS once they exceed 500K
OFFSTREAM_FLUSH_THRESHOLD=500000
# Check each stream every 20 seconds
OFFSTREAM_CHECK_INTERVAL=20
# Listen port
PORT=8000
# Enable SQLAlchemy 2.0 deprecation mode
SQLALCHEMY_WARN_20=1
