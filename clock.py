import urllib.request

from zoneinfo import ZoneInfo
from datetime import datetime

now = datetime.now(tz=ZoneInfo("America/New_York"))
# Ping itself to prevent idling
# Every day from 11am to 8pm ET
if 11 <= now.hour <= 20:
    urllib.request.urlopen("https://offstream.herokuapp.com/").read()
