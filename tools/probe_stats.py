"""Kontroll: är ODDS_API_KEY fortfarande en giltig The Odds API-nyckel? /v4/sports kostar inga krediter. Skriver aldrig nyckeln."""
import json, os, sys, urllib.request, urllib.error, urllib.parse

key = (os.environ.get("ODDS_API_KEY") or "").strip()
print("ODDS_API_KEY satt:", bool(key), "| längd:", len(key))
if not key:
    sys.exit(0)
url = "https://api.the-odds-api.com/v4/sports/?" + urllib.parse.urlencode({"apiKey": key})
try:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "propsbot"}), timeout=30) as r:
        h = {k.lower(): v for k, v in r.headers.items()}
        body = json.loads(r.read())
        print("STATUS", r.status, "| sporter:", len(body), "| krediter kvar:", h.get("x-requests-remaining"), "| använda:", h.get("x-requests-used"))
except urllib.error.HTTPError as e:
    print("STATUS", e.code, e.read()[:200].decode("utf8", "replace"))
