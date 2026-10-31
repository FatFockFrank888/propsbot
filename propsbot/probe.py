"""Provar om externa datakällor svarar från den här servern (för beslut om nya källor)."""
import urllib.request

from .sources.http import UA

URLS = {
    "nba_stats": "https://stats.nba.com/stats/leaguedashplayerstats?LeagueID=00&Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame&MeasureType=Base",
    "nba_cdn_schedule": "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
    "nba_cdn_scoreboard": "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
    "basketball_reference": "https://www.basketball-reference.com/leagues/NBA_2026_per_game.html",
    "hashtag_basketball": "https://hashtagbasketball.com/nba-defense-vs-position",
    "rotowire_injuries": "https://www.rotowire.com/basketball/tables/injury-report.php?team=ALL&pos=ALL",
    "props_cash": "https://www.props.cash/",
    "balldontlie": "https://api.balldontlie.io/v1/players?per_page=1",
    "espn_nba_injuries": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries",
}


def main() -> None:
    out = []
    for name, url in URLS.items():
        try:
            h = {"User-Agent": UA, "Accept": "application/json,text/html"}
            if "stats.nba.com" in url:
                h.update({"Referer": "https://www.nba.com/", "Origin": "https://www.nba.com",
                          "x-nba-stats-origin": "stats", "x-nba-stats-token": "true"})
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=20) as r:
                body = r.read(400).decode("utf-8", "replace").replace("\n", " ")
                out.append(f"{name}: {r.status} {body[:120]}")
        except Exception as e:
            out.append(f"{name}: FEL {type(e).__name__} {getattr(e, 'code', '')} {str(e)[:80]}")
    print("::notice title=probe::" + "%0A".join(x.replace("%", "%25") for x in out))


if __name__ == "__main__":
    main()
