import urllib.request

from zoneinfo import ZoneInfo
from datetime import datetime

now = datetime.now(tz=ZoneInfo("America/New_York"))
# Ping itself to prevent idling
# Every day except Thursdays from 11am to 8pm ET
if now.weekday() != 3 and 11 <= now.hour <= 21:
    urllib.request.urlopen("https://offstream.herokuapp.com/").read()
