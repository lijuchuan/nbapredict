#!/usr/bin/env python3
"""
抓取 RotoWire 当日 NBA 首发与「MAY NOT PLAY」名单，并从 NBA 官网伤病报告索引页选取最新 PDF，
解析为文本与尽量结构化的球员行，合并写入一个 JSON 文件。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from urllib.request import Request, urlopen

ROTOWIRE_URL = "https://www.rotowire.com/basketball/nba-lineups.php"
NBA_INJURY_INDEX_URL = "https://official.nba.com/nba-injury-report-2025-26-season/"
PDF_HREF_RE = re.compile(
    r"https://ak-static\.cms\.nba\.com/referee/injury/Injury-Report_\d{4}-\d{2}-\d{2}_\d{2}_\d{2}(?:AM|PM)\.pdf"
)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def _http_get(url: str, timeout: int = 45) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _http_get_text(url: str, timeout: int = 45) -> str:
    return _http_get(url, timeout=timeout).decode("utf-8", "replace")


def _pdf_timestamp_key(url: str) -> tuple[str, int]:
    """文件名 Injury-Report_YYYY-MM-DD_HH_MMAM|PM.pdf -> 可排序键。"""
    m = re.search(
        r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)\.pdf",
        url,
    )
    if not m:
        return ("", 0)
    date_s, hh, mm, ap = m.groups()
    h = int(hh)
    minute = int(mm)
    if ap == "AM":
        hour24 = 0 if h == 12 else h
    else:
        hour24 = 12 if h == 12 else h + 12
    minutes = hour24 * 60 + minute
    return (date_s, minutes)


def pick_latest_pdf_url(html: str) -> str | None:
    found = PDF_HREF_RE.findall(html)
    if not found:
        return None
    return max(found, key=_pdf_timestamp_key)


def parse_rotowire_lineups(html: str) -> list[dict[str, Any]]:
    """解析 lineup is-nba 区块：首发五人、确认/预期、伤停侧栏。"""
    parts = html.split('<div class="lineup is-nba"')[1:]
    games: list[dict[str, Any]] = []
    team_re = re.compile(
        r'class="lineup__mteam [^"]+">\s*([^<]+?)\s*<span class="lineup__wl">\(([^)]*)\)</span>',
        re.S,
    )
    time_re = re.compile(r'<div class="lineup__time">([^<]+)</div>')

    for sec in parts:
        abbrs = re.findall(r'<div class="lineup__abbr">(.*?)</div>', sec)
        teams = team_re.findall(sec)
        visit_m = re.search(r'<ul class="lineup__list is-visit">(.*?)</ul>', sec, re.S)
        home_m = re.search(r'<ul class="lineup__list is-home">(.*?)</ul>', sec, re.S)
        if len(teams) < 2 or not visit_m or not home_m:
            continue

        tm = time_re.search(sec)
        away_name = teams[0][0].strip()
        home_name = teams[1][0].strip()
        game: dict[str, Any] = {
            "time_et": tm.group(1).strip() if tm else None,
            "away_abbr": abbrs[0].strip() if len(abbrs) > 0 else None,
            "home_abbr": abbrs[1].strip() if len(abbrs) > 1 else None,
            "away_team": away_name,
            "home_team": home_name,
            "away_record": teams[0][1].strip(),
            "home_record": teams[1][1].strip(),
            "away": _parse_lineup_side_ul(visit_m.group(1)),
            "home": _parse_lineup_side_ul(home_m.group(1)),
        }
        games.append(game)
    return games


def _parse_lineup_side_ul(ul_inner: str) -> dict[str, Any]:
    if "is-confirmed" in ul_inner:
        kind = "confirmed"
    elif "is-expected" in ul_inner:
        kind = "expected"
    else:
        kind = None

    chunks = re.split(
        r'<li class="lineup__title is-middle">MAY NOT PLAY</li>',
        ul_inner,
        maxsplit=1,
    )
    starters_part = chunks[0]
    out_part = chunks[1] if len(chunks) > 1 else ""

    player_li = re.compile(
        r'<li class="lineup__player[^"]*"[^>]*>\s*'
        r'<div class="lineup__pos"[^>]*>(.*?)</div>\s*'
        r'<a[^>]*title="([^"]+)"[^>]*>([^<]*)</a>',
        re.S,
    )
    starters: list[dict[str, str]] = []
    for pos, full_name, short in player_li.findall(starters_part):
        pos = re.sub(r"\s+", " ", pos.replace("\n", " ")).strip()
        if not pos:
            continue
        starters.append(
            {
                "position": pos,
                "name": full_name.strip(),
                "name_short": short.strip(),
            }
        )
        if len(starters) >= 5:
            break

    inj_re = re.compile(
        r'<li class="lineup__player[^"]*has-injury-status[^"]*"[^>]*>\s*'
        r'<div class="lineup__pos"[^>]*>(.*?)</div>\s*'
        r'<a[^>]*title="([^"]+)"[^>]*>([^<]*)</a>\s*'
        r'<span class="lineup__inj">([^<]+)</span>',
        re.S,
    )
    may_not_play: list[dict[str, str]] = []
    for pos, full_name, short, tag in inj_re.findall(out_part):
        pos = re.sub(r"\s+", " ", pos.replace("\n", " ")).strip()
        may_not_play.append(
            {
                "position": pos,
                "name": full_name.strip(),
                "name_short": short.strip(),
                "status": tag.strip(),
            }
        )

    return {
        "lineup_status": kind,
        "starters": starters,
        "may_not_play": may_not_play,
    }


def _split_official_pdf_by_game(full_text: str) -> list[dict[str, str]]:
    """
    按「比赛时间 + 对阵」锚点切分官方 PDF 文本。
    常见形式：'04/03/2026 07:00(ET) IND@CHA'；同日报后续场次可能省略日期，仅 '07:30(ET) ATL@BKN'。
    """
    header_re = re.compile(
        r"(\d{2}/\d{2}/\d{4}\s+)?(\d{2}:\d{2})\(ET\)\s+([A-Z0-9]+@[A-Z0-9]+)"
    )
    matches = list(header_re.finditer(full_text))
    if not matches:
        return []

    sections: list[dict[str, Any]] = []
    last_date = ""
    # 同一时间档多场比赛时，后续对阵可能以单独一行「AWY@HOM」出现（无日期时间前缀）
    embedded_matchup_re = re.compile(
        r"(?:^|\n)([A-Z0-9]{2,4}@[A-Z0-9]{2,4})\s+(?=[A-Z][a-z]+[A-Z][a-z])"
    )
    for i, m in enumerate(matches):
        date_part = (m.group(1) or "").strip()
        if date_part:
            last_date = date_part
        time_et = m.group(2)
        matchup = m.group(3)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        body = full_text[m.end() : end].strip()
        header_line = f"{last_date} {time_et}(ET) {matchup}".strip()
        segments: list[dict[str, str]] = []
        subs = list(embedded_matchup_re.finditer(body))
        if not subs:
            segments.append({"matchup": matchup, "text": body})
        else:
            head = body[: subs[0].start()].strip()
            if head:
                segments.append({"matchup": matchup, "text": head})
            for j, sm in enumerate(subs):
                sub_mup = sm.group(1)
                t0 = sm.end()
                t1 = subs[j + 1].start() if j + 1 < len(subs) else len(body)
                segments.append({"matchup": sub_mup, "text": body[t0:t1].strip()})
        sections.append(
            {
                "game_date": last_date,
                "game_time_et": time_et,
                "matchup": matchup,
                "header_line": header_line,
                "injury_block_text": body,
                "segments": segments,
            }
        )
    return sections


def fetch_nba_official_bundle() -> dict[str, Any]:
    out: dict[str, Any] = {
        "index_url": NBA_INJURY_INDEX_URL,
        "latest_pdf_url": None,
        "pdf_text": None,
        "by_game": [],
        "pdf_parse_error": None,
    }
    try:
        index_html = _http_get_text(NBA_INJURY_INDEX_URL, timeout=45)
    except Exception as e:
        out["pdf_parse_error"] = f"index_fetch_failed:{e}"
        return out

    pdf_url = pick_latest_pdf_url(index_html)
    out["latest_pdf_url"] = pdf_url
    if not pdf_url:
        out["pdf_parse_error"] = "no_pdf_links_found"
        return out

    try:
        pdf_bytes = _http_get(pdf_url, timeout=60)
    except Exception as e:
        out["pdf_parse_error"] = f"pdf_fetch_failed:{e}"
        return out

    try:
        import pdfplumber  # type: ignore
    except ImportError:
        out["pdf_parse_error"] = "pdfplumber_not_installed"
        return out

    try:
        text_parts: list[str] = []
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        full_text = "\n".join(text_parts)
        out["pdf_text"] = full_text
        out["by_game"] = _split_official_pdf_by_game(full_text)
    except Exception as e:
        out["pdf_parse_error"] = f"pdf_extract_failed:{e}"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="NBA 首发+伤停 JSON 抓取")
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help="输出 JSON 路径；默认 data/nba_lineups_injuries_<UTC日期>.json",
    )
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    out_path = args.output or (
        f"data/nba_lineups_injuries_{now.date().isoformat()}.json"
    )

    payload: dict[str, Any] = {
        "fetched_at_utc": now.isoformat(),
        "sources": {
            "rotowire_lineups": ROTOWIRE_URL,
            "nba_official_injury_index": NBA_INJURY_INDEX_URL,
        },
        "rotowire": {"games": [], "error": None},
        "nba_official": {},
    }

    try:
        rw_html = _http_get_text(ROTOWIRE_URL, timeout=45)
        payload["rotowire"]["games"] = parse_rotowire_lineups(rw_html)
    except Exception as e:
        payload["rotowire"]["error"] = str(e)

    payload["nba_official"] = fetch_nba_official_bundle()

    raw = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(raw)
    except OSError as e:
        print(f"写入失败 {out_path}: {e}", file=sys.stderr)
        print(raw)
        return 1

    print(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
