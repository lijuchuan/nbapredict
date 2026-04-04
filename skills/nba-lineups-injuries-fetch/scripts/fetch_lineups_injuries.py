#!/usr/bin/env python3
"""
抓取 RotoWire 当日首发与 MAY NOT PLAY、ESPN NBA 伤病表、NBA 官网最新伤病 PDF；
可选抓取澳客 m 站篮球让分盘（hwl）change.php 的盘口与水位变化记录。
多源结果写入一个 JSON 文件。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

BEIJING_TZ = ZoneInfo("Asia/Shanghai")

ROTOWIRE_URL = "https://www.rotowire.com/basketball/nba-lineups.php"
NBA_INJURY_INDEX_URL = "https://official.nba.com/nba-injury-report-2025-26-season/"
ESPN_INJURIES_URL = "https://www.espn.com/nba/injuries"
OKOOO_BASE = "https://m.okooo.com"
OKOOO_REFERER = "https://m.okooo.com/live/?LotteryType=lancai"
OKOOO_LIVE_LANCAI_URL = f"{OKOOO_BASE}/live/?LotteryType=lancai"
# 澳客 live 页 NBA 条目（含篮球竞彩 history 链）
OKOOO_LIVE_NBA_ITEM_RE = re.compile(
    r'<div class="liveItem jsLiveItem" leagueId="(?P<league>\d+)">\s*<!--(?P<match_id>\d+) -->'
    r'.*?<div class="liveItemls">(?P<match_no>[^<]+) <font color="">(?P<league_name>[^<]+)</font>'
    r'.*?<p class="name fl txtright">(?P<away>[^<]+)'
    r'.*?<span class="gray9 font12" id="status_\d+" status="" >(?P<status>.*?)</span>'
    r'.*?<span class="bifentxt gray9" id="score_(?P<score_id>\d+)">(?P<time_or_score>[^<]+)</span>'
    r'.*?<p class="name fl txtleft">(?P<home>[^<]+)</p>'
    r'.*?<div href="(?P<history_href>/match/basketball/history\.php\?LotteryType=SportteryWL&MatchID=\d+&from=%2Flive%2F)"',
    re.S,
)
# 澳客篮球让分盘「变化列表」表格行：左列水位/赔率、中间让分、右列水位/赔率、时间说明
CHANGE_ROW_RE = re.compile(
    r"<tr>\s*<td><span[^>]*>(.*?)</span><span style=\"width:48px;\s*\"?\s*>(.*?)</span><span[^>]*>(.*?)</span></td>\s*<td class=\"timetd\">(.*?)</td>\s*</tr>",
    re.S,
)
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


def _http_get_okooo_gbk(url: str, timeout: int = 45) -> str:
    """澳客 m 站多为 GBK，需 Referer 降低异常。"""
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": OKOOO_REFERER,
    }
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("gbk", "replace")


def _strip_okooo_cell(html_fragment: str) -> str:
    return re.sub(r"<[^>]+>", "", html_fragment).strip()


def _norm_cn_compact(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


def _cn_hint_matches_team(hint: str, team_cn: str) -> bool:
    """队名子串互含（适应「森林狼」vs「明尼苏达森林狼」）。"""
    h = _norm_cn_compact(hint)
    t = _norm_cn_compact(team_cn)
    if not h or not t:
        return False
    return h in t or t in h


def parse_okooo_live_nba_games(html: str) -> list[dict[str, str]]:
    """从篮彩 live 页解析当前列表中的 NBA 场次（match_id + 主客中文名）。"""
    rows: list[dict[str, str]] = []
    for m in OKOOO_LIVE_NBA_ITEM_RE.finditer(html):
        league_name = m.group("league_name").strip()
        if league_name != "NBA":
            continue
        rows.append(
            {
                "match_id": m.group("match_id"),
                "league_name": league_name,
                "away_cn": m.group("away").strip(),
                "home_cn": m.group("home").strip(),
                "time_or_score_bj": m.group("time_or_score").strip(),
            }
        )
    return rows


def lookup_okooo_mid_by_team_cn(
    away_hint: str,
    home_hint: str,
    games: list[dict[str, str]],
) -> dict[str, Any]:
    """
    用主客中文关键词在 NBA 列表中找 match_id。
    先按「客+主」顺序匹配，若无结果再试主客对调。
    """
    out: dict[str, Any] = {
        "match_id": None,
        "swapped": False,
        "candidates": [],
        "ambiguous": False,
    }

    def collect(ah: str, hh: str) -> list[dict[str, str]]:
        hits: list[dict[str, str]] = []
        for g in games:
            if _cn_hint_matches_team(ah, g["away_cn"]) and _cn_hint_matches_team(
                hh, g["home_cn"]
            ):
                hits.append(g)
        return hits

    cand = collect(away_hint, home_hint)
    swapped = False
    if not cand:
        cand = collect(home_hint, away_hint)
        swapped = bool(cand)
    out["candidates"] = cand
    out["swapped"] = swapped
    if len(cand) == 1:
        out["match_id"] = cand[0]["match_id"]
    elif len(cand) > 1:
        out["ambiguous"] = True
        out["match_id"] = cand[0]["match_id"]
    return out


def build_okooo_hwl_change_url(mid: str, pid: str = "3", c: str = "1") -> str:
    """篮球让分盘水位/盘口变化页（Type=hwl）。"""
    return (
        f"{OKOOO_BASE}/match/basketball/change.php?"
        f"mid={mid}&pid={pid}&Type=hwl&c={c}"
    )


def parse_okooo_hwl_change_html(html: str) -> dict[str, Any]:
    """从变化页 HTML 解析当前选中的博彩公司与变化行。"""
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = _strip_okooo_cell(title_m.group(1)) if title_m else ""
    book_m = re.search(r'<a class="changeNav selected"[^>]*>([^<]+)</a>', html)
    book = _strip_okooo_cell(book_m.group(1)) if book_m else None
    tbl_m = re.search(r'class="changeTable">(.*?)</table>', html, re.S)
    inner = tbl_m.group(1) if tbl_m else ""
    changes: list[dict[str, str]] = []
    for a, b, c, d in CHANGE_ROW_RE.findall(inner):
        changes.append(
            {
                "left": _strip_okooo_cell(a),
                "line": _strip_okooo_cell(b),
                "right": _strip_okooo_cell(c),
                "time": _strip_okooo_cell(d),
            }
        )
    return {"title": title, "book_name_zh": book, "changes": changes}


def fetch_okooo_hwl_change_bundle(url: str) -> dict[str, Any]:
    """抓取单条 change.php（hwl）并解析为结构化变化列表。"""
    out: dict[str, Any] = {
        "url": url,
        "query": {},
        "page_title": None,
        "book_name_zh": None,
        "changes": [],
        "error": None,
    }
    try:
        qs = parse_qs(urlparse(url).query)
        out["query"] = {k: (v[0] if len(v) == 1 else v) for k, v in qs.items()}
    except Exception:
        pass
    try:
        html = _http_get_okooo_gbk(url)
    except Exception as e:
        out["error"] = str(e)
        return out
    parsed = parse_okooo_hwl_change_html(html)
    out["page_title"] = parsed["title"]
    out["book_name_zh"] = parsed["book_name_zh"]
    out["changes"] = parsed["changes"]
    if not out["changes"]:
        out["empty_notice_zh"] = (
            "该页「变化列表」表格为空；常见于所选公司 pid 无记录或比赛已关闭。"
            "可在 handicap 页换其它公司的变化链接（不同 pid），例如竞彩官方 pid=2。"
        )
    return out


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


def parse_espn_injuries_page(html: str) -> list[dict[str, Any]]:
    """
    解析 ESPN injuries 页中每个 ResponsiveTable：队名 + 球员行（姓名、位置、预计回归、状态、备注）。
    """
    blocks = html.split('<div class="ResponsiveTable Table__league-injuries">')[1:]
    team_name_re = re.compile(
        r'<span class="injuries__teamName ml2">([^<]+)</span>'
    )
    row_re = re.compile(
        r'<tr class="Table__TR Table__TR--sm[^"]*"[^>]*>(.*?)</tr>',
        re.S,
    )
    teams_out: list[dict[str, Any]] = []
    for block in blocks:
        tm = team_name_re.search(block)
        if not tm:
            continue
        team = tm.group(1).strip()
        players: list[dict[str, str]] = []
        for rm in row_re.finditer(block):
            tr = rm.group(1)
            name_m = re.search(r'<a class="AnchorLink"[^>]*>([^<]+)</a>', tr)
            if not name_m:
                continue
            pos_m = re.search(r'<td class="col-pos Table__TD">([^<]*)</td>', tr)
            date_m = re.search(r'<td class="col-date Table__TD">([^<]*)</td>', tr)
            stat_m = re.search(r'<td class="col-stat Table__TD">(.*?)</td>', tr, re.S)
            desc_m = re.search(r'<td class="col-desc Table__TD">([^<]*)</td>', tr)
            status = ""
            if stat_m:
                inner = stat_m.group(1)
                s2 = re.search(r">([^<]+)</span>", inner)
                status = (
                    s2.group(1).strip()
                    if s2
                    else re.sub(r"<[^>]+>", "", inner).strip()
                )
            players.append(
                {
                    "name": name_m.group(1).strip(),
                    "position": (pos_m.group(1).strip() if pos_m else ""),
                    "est_return_date": (date_m.group(1).strip() if date_m else ""),
                    "status": status,
                    "comment": (desc_m.group(1).strip() if desc_m else ""),
                }
            )
        teams_out.append({"team": team, "players": players})
    return teams_out


def _espn_team_tokens(full_name: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", full_name.lower())


def _find_espn_team_row(
    rotowire_team_name: str, espn_teams: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """
    将 RotoWire 队名对齐到 ESPN 完整队名。
    用「队名片段最后若干 token」匹配，避免 'Nets' 误命中 'Hornets'（子串/后缀陷阱）。
    """
    rw = rotowire_team_name.strip()
    if not rw:
        return None
    rwn = rw.lower()
    rw_parts = rwn.split()
    names = [t["team"] for t in espn_teams]

    for t in espn_teams:
        if t["team"].lower() == rwn:
            return t

    hits: list[str] = []
    for full in names:
        toks = _espn_team_tokens(full)
        if not toks:
            continue
        if toks[-1] == rwn:
            hits.append(full)
            continue
        if len(rw_parts) >= 2 and len(toks) >= 2:
            if toks[-2] == rw_parts[-2] and toks[-1] == rw_parts[-1]:
                hits.append(full)
    if len(hits) == 1:
        return next(t for t in espn_teams if t["team"] == hits[0])
    if len(hits) > 1:
        return next(t for t in espn_teams if t["team"] == max(hits, key=len))

    aliases = {
        "blazers": "Portland Trail Blazers",
        "sixers": "Philadelphia 76ers",
        "wolves": "Minnesota Timberwolves",
    }
    if rwn in aliases:
        target = aliases[rwn]
        for t in espn_teams:
            if t["team"] == target:
                return t
    return None


def merge_rotowire_espn_games(
    rw_games: list[dict[str, Any]], espn_teams: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """每场 RotoWire 对阵挂载对应 ESPN 全队伤病表（按队名对齐）。"""
    merged: list[dict[str, Any]] = []
    for g in rw_games:
        away = g.get("away_team") or ""
        home = g.get("home_team") or ""
        away_row = _find_espn_team_row(away, espn_teams)
        home_row = _find_espn_team_row(home, espn_teams)
        entry = {
            **g,
            "injury_crosswalk": {
                "away": {
                    "rotowire_name": away,
                    "espn_team": away_row["team"] if away_row else None,
                    "espn_players": (
                        away_row["players"] if away_row else []
                    ),
                },
                "home": {
                    "rotowire_name": home,
                    "espn_team": home_row["team"] if home_row else None,
                    "espn_players": (
                        home_row["players"] if home_row else []
                    ),
                },
            },
        }
        merged.append(entry)
    return merged


def resolve_data_archive_output_path(output_arg: str, bj_date: str) -> str:
    """
    爬取结果统一落在项目 data 目录下、按北京日历日子目录存放：
    data/<YYYY-MM-DD>/<相对路径或默认文件名>
    """
    default_name = f"nba_lineups_injuries_{bj_date}.json"
    raw = (output_arg or "").strip()
    if not raw:
        rel = default_name
    else:
        rel = raw.replace("\\", "/")
        while rel.startswith("./"):
            rel = rel[2:]
        if rel.startswith("data/"):
            rel = rel[5:].lstrip("/")
        rel_os = os.path.normpath(rel)
        if os.path.isabs(rel_os) or rel_os.startswith(".."):
            rel_os = os.path.basename(rel_os) or default_name
        rel = rel_os
    return os.path.join("data", bj_date, rel)


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
        help=(
            "输出文件相对「当日归档目录」的路径或文件名；实际写入 data/<北京时间YYYY-MM-DD>/ 下。"
            "留空则默认为该目录下的 nba_lineups_injuries_<同日>.json"
        ),
    )
    parser.add_argument(
        "--okooo-hwl-change-url",
        action="append",
        default=[],
        metavar="URL",
        help=(
            "澳客篮球让分盘变化页 URL，可重复传入多条。"
            "示例：https://m.okooo.com/match/basketball/change.php?mid=5378517&pid=3&Type=hwl&c=1"
        ),
    )
    parser.add_argument(
        "--okooo-mid",
        default="",
        metavar="MID",
        help="澳客比赛 mid；与 --okooo-hwl-pid 组合生成 hwl 变化页并抓取",
    )
    parser.add_argument(
        "--okooo-hwl-pid",
        default="3",
        metavar="PID",
        help="变化页博彩公司 pid（默认 3=竞彩单选）；无数据时可试 2=竞彩官方等",
    )
    parser.add_argument(
        "--okooo-live-away-cn",
        default="",
        metavar="TEXT",
        help=(
            "与 --okooo-live-home-cn 成对使用：澳客 live 页「客队」中文关键词（不必写全名，如 森林狼）"
        ),
    )
    parser.add_argument(
        "--okooo-live-home-cn",
        default="",
        metavar="TEXT",
        help="主队中文关键词；脚本会拉取篮彩 live 列表筛 NBA 后匹配 match_id，再拼 hwl 变化页",
    )
    args = parser.parse_args()
    la_live = args.okooo_live_away_cn.strip()
    lh_live = args.okooo_live_home_cn.strip()
    if (la_live and not lh_live) or (lh_live and not la_live):
        print(
            "错误：--okooo-live-away-cn 与 --okooo-live-home-cn 须同时提供或同时省略。",
            file=sys.stderr,
        )
        return 2
    now_utc = datetime.now(timezone.utc)
    now_beijing = now_utc.astimezone(BEIJING_TZ)
    bj_date = now_beijing.date().isoformat()
    out_path = resolve_data_archive_output_path(args.output, bj_date)

    payload: dict[str, Any] = {
        "fetched_at_utc": now_utc.isoformat(),
        "fetched_at_beijing": now_beijing.isoformat(),
        "archive_date_beijing": bj_date,
        "output_path": out_path,
        "output_storage_note_zh": (
            "抓取结果统一写入仓库根下 data/<北京时间YYYY-MM-DD>/ 目录；"
            "archive_date_beijing 与目录名一致。"
        ),
        "sources": {
            "rotowire_lineups": ROTOWIRE_URL,
            "nba_official_injury_index": NBA_INJURY_INDEX_URL,
            "espn_injuries": ESPN_INJURIES_URL,
        },
        "rotowire": {"games": [], "error": None},
        "espn": {
            "teams": [],
            "error": None,
            "url": ESPN_INJURIES_URL,
        },
        "nba_official": {},
        "merged": {
            "games": [],
            "fusion_notes_zh": (
                "首发以 RotoWire 为准（区分 Confirmed/Expected）。"
                "伤停优先级：NBA 官方 PDF > RotoWire MAY NOT PLAY；"
                "ESPN 为第三方汇总，可与前两源对照，冲突时以官方为准。"
            ),
        },
        "okooo_hwl_change": {
            "fetches": [],
            "interpretation_zh": (
                "澳客篮球让分变化页：每条 changes 为一次盘口/水位变动。"
                "left、right 为页面从左到右两列（多为客队/主队方向水位或赔率，以当场页面为准）；"
                "line 为让分盘口；time 为站内相对时间文案（如赛前xx小时）。"
            ),
        },
    }

    ok_urls: list[str] = list(args.okooo_hwl_change_url)
    if args.okooo_mid.strip():
        ok_urls.append(
            build_okooo_hwl_change_url(
                args.okooo_mid.strip(),
                args.okooo_hwl_pid.strip() or "3",
            )
        )
    pid_hwl = args.okooo_hwl_pid.strip() or "3"
    if la_live and lh_live:
        tl: dict[str, Any] = {
            "away_hint": la_live,
            "home_hint": lh_live,
            "live_url": OKOOO_LIVE_LANCAI_URL,
        }
        try:
            live_html = _http_get_okooo_gbk(OKOOO_LIVE_LANCAI_URL)
            nba_games = parse_okooo_live_nba_games(live_html)
            tl["nba_games_on_page"] = len(nba_games)
            tl["nba_games"] = nba_games
            lk = lookup_okooo_mid_by_team_cn(la_live, lh_live, nba_games)
            tl.update(lk)
            if lk.get("match_id"):
                ch_url = build_okooo_hwl_change_url(str(lk["match_id"]), pid_hwl)
                tl["resolved_hwl_change_url"] = ch_url
                ok_urls.append(ch_url)
                if lk.get("ambiguous"):
                    tl["warning_zh"] = (
                        "匹配到多条 NBA 场次，已使用第一条的 match_id；"
                        "建议改用 --okooo-mid 精确指定。"
                    )
                if lk.get("swapped"):
                    tl["note_zh"] = (
                        "已按主客对调后匹配成功（你输入的客/主与 live 页展示顺序不一致）。"
                    )
            else:
                tl["error"] = (
                    "当前 live 页的 NBA 列表中，用语义关键词未匹配到场次。"
                    "可能当日列表尚无 NBA、队名写法不同，或请改用 --okooo-mid / --okooo-hwl-change-url。"
                )
        except Exception as e:
            tl["error"] = f"live_fetch_or_parse_failed:{e}"
        payload["okooo_hwl_change"]["team_lookup"] = tl

    seen: set[str] = set()
    for u in ok_urls:
        if u in seen:
            continue
        seen.add(u)
        payload["okooo_hwl_change"]["fetches"].append(fetch_okooo_hwl_change_bundle(u))
    if not ok_urls:
        payload["okooo_hwl_change"]["skipped_zh"] = (
            "未指定 --okooo-hwl-change-url、--okooo-mid，或未成功通过 "
            "--okooo-live-away-cn / --okooo-live-home-cn 解析出 match_id；已跳过澳客变化页抓取。"
        )

    try:
        rw_html = _http_get_text(ROTOWIRE_URL, timeout=45)
        payload["rotowire"]["games"] = parse_rotowire_lineups(rw_html)
    except Exception as e:
        payload["rotowire"]["error"] = str(e)

    try:
        espn_html = _http_get_text(ESPN_INJURIES_URL, timeout=45)
        payload["espn"]["teams"] = parse_espn_injuries_page(espn_html)
    except Exception as e:
        payload["espn"]["error"] = str(e)

    payload["nba_official"] = fetch_nba_official_bundle()

    payload["merged"]["games"] = merge_rotowire_espn_games(
        payload["rotowire"]["games"],
        payload["espn"]["teams"],
    )

    raw = json.dumps(payload, ensure_ascii=False, indent=2)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
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
