"""Provar om externa datakällor svarar från den här servern (för beslut om nya källor)."""
import urllib.request

from .sources.http import UA

URLS = {
    "sofascore": "https://api.sofascore.com/api/v1/sport/football/scheduled-events/2026-11-01",
    "sofascore_www": "https://www.sofascore.com/api/v1/sport/football/scheduled-events/2026-11-01",
    "fotmob": "https://www.fotmob.com/api/data/matches?date=20261101",
    "fotmob_old": "https://www.fotmob.com/api/matches?date=20261101",
    "understat": "https://understat.com/league/EPL/2025",
    "fbref": "https://fbref.com/en/comps/9/Premier-League-Stats",
}


def main() -> None:
    out = []
    for name, url in URLS.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/html"})
            with urllib.request.urlopen(req, timeout=20) as r:
                body = r.read(400).decode("utf-8", "replace").replace("\n", " ")
                out.append(f"{name}: {r.status} {body[:120]}")
        except Exception as e:
            out.append(f"{name}: FEL {type(e).__name__} {getattr(e, 'code', '')} {str(e)[:80]}")
    print("::notice title=probe::" + "%0A".join(x.replace("%", "%25") for x in out))


if __name__ == "__main__":
    main()
