import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://sports.yahoo.com"
TEAMS_URL = f"{BASE}/nba/teams/"
OUT_DIR = Path("data")
OUT_DIR.mkdir(exist_ok=True)
JSON_OUT = OUT_DIR / "nba_yahoo_rosters.json"
CSV_OUT = OUT_DIR / "nba_yahoo_rosters.csv"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
})


def normalize_embedded_json_text(page_text: str) -> str:
    # Yahoo embeds JSON as escaped strings inside the HTML.
    return page_text.encode("utf-8").decode("unicode_escape").encode("latin1", "ignore").decode("utf-8", "ignore")


def extract_team_slugs(teams_html: str):
    slugs = sorted(set(re.findall(r'/nba/teams/([a-z-]+)/roster/', teams_html)))
    return slugs


def extract_team_name(text: str, slug: str) -> str:
    m = re.search(r'<meta property="og:title" content="([^"]+?) Team Roster - Yahoo Sports"', text)
    if m:
        return m.group(1)
    return slug.replace("-", " ").title()


def extract_players(text: str):
    starts = [m.start() for m in re.finditer(r'\{"playerId":"nba\.p\.[0-9]+"', text)]
    decoder = json.JSONDecoder()
    players = {}
    for start in starts:
        try:
            obj, _ = decoder.raw_decode(text[start:])
        except Exception:
            continue
        if not isinstance(obj, dict) or "playerId" not in obj or "displayName" not in obj:
            continue
        if "displayHeight" not in obj:
            continue
        players[obj["playerId"]] = obj
    return list(players.values())


def flatten_player(team_slug: str, team_name: str, player: dict):
    injury = player.get("injury") or {}
    status = player.get("status") or {}
    positions = player.get("positions") or []
    return {
        "team_slug": team_slug,
        "team_name": team_name,
        "player_id": player.get("playerId"),
        "name": player.get("displayName"),
        "first_name": player.get("firstName"),
        "last_name": player.get("lastName"),
        "uniform_number": player.get("uniformNumber"),
        "positions": "/".join([p.get("abbreviation", "") for p in positions if p.get("abbreviation")]),
        "position_names": "/".join([p.get("name", "") for p in positions if p.get("name")]),
        "status": status.get("displayAbbreviation"),
        "status_id": status.get("playerStatusId"),
        "active": player.get("active"),
        "age": player.get("age"),
        "height": player.get("displayHeight"),
        "weight": player.get("weight"),
        "birth_date": player.get("birthDate"),
        "birth_city": player.get("birthCity"),
        "birth_state": player.get("birthState"),
        "birth_country": player.get("birthCountry"),
        "college": player.get("college"),
        "first_year": player.get("firstYear"),
        "last_year": player.get("lastYear"),
        "experience_years": player.get("experienceInYears"),
        "injury_type": injury.get("injuryType"),
        "injury_notes": injury.get("note") or injury.get("description"),
        "player_url": ((player.get("alias") or {}).get("url")),
        "headshot_url": ((player.get("suggestedHeadshot") or {}).get("url")),
        "source_url": f"{BASE}/nba/teams/{team_slug}/roster/",
    }


def main():
    teams_page = session.get(TEAMS_URL, timeout=30)
    teams_page.raise_for_status()
    team_slugs = extract_team_slugs(teams_page.text)

    results = []
    flat_rows = []
    for slug in team_slugs:
        url = f"{BASE}/nba/teams/{slug}/roster/"
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        normalized = normalize_embedded_json_text(resp.text)
        team_name = extract_team_name(resp.text, slug)
        players = extract_players(normalized)
        players_sorted = sorted(players, key=lambda p: (p.get("lastName") or "", p.get("firstName") or ""))
        results.append({
            "team_slug": slug,
            "team_name": team_name,
            "source_url": url,
            "player_count": len(players_sorted),
            "players": [flatten_player(slug, team_name, p) for p in players_sorted],
        })
        flat_rows.extend([flatten_player(slug, team_name, p) for p in players_sorted])

    payload = {
        "source": TEAMS_URL,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "team_count": len(results),
        "player_count": len(flat_rows),
        "teams": results,
    }

    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = list(flat_rows[0].keys()) if flat_rows else []
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat_rows)

    print(f"Wrote {JSON_OUT} and {CSV_OUT}")
    print(f"Teams: {len(results)} | Players: {len(flat_rows)}")


if __name__ == "__main__":
    main()
