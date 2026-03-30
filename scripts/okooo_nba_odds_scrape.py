#!/usr/bin/env python3
import json
import re
import time
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = 'https://m.okooo.com'
LIVE_URL = f'{BASE}/live/?LotteryType=lancai'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36'

session = requests.Session()
session.headers.update({'User-Agent': UA})


def fetch(url: str, referer: str | None = None) -> str:
    headers = {}
    if referer:
        headers['Referer'] = referer
    resp = session.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = 'gbk'
    return resp.text


def clean_text(s: str) -> str:
    s = unescape(re.sub(r'<[^>]+>', ' ', s))
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def parse_live_matches(html: str):
    pattern = re.compile(
        r'<div class="liveItem jsLiveItem" leagueId="(?P<league>\d+)">\s*<!--(?P<match_id>\d+) -->'
        r'.*?<div class="liveItemls">(?P<match_no>[^<]+) <font color="">(?P<league_name>[^<]+)</font>'
        r'.*?<p class="name fl txtright">(?P<away>[^<]+)'
        r'.*?<span class="gray9 font12" id="status_\d+" status="" >(?P<status>.*?)</span>'
        r'.*?<span class="bifentxt gray9" id="score_\d+">(?P<time_or_score>[^<]+)</span>'
        r'.*?<p class="name fl txtleft">(?P<home>[^<]+)</p>'
        r'.*?<div href="(?P<history_href>/match/basketball/history\.php\?LotteryType=SportteryWL&MatchID=\d+&from=%2Flive%2F)"',
        re.S,
    )
    matches = []
    for m in pattern.finditer(html):
        league_name = clean_text(m.group('league_name'))
        if league_name != 'NBA':
            continue
        matches.append({
            'match_id': m.group('match_id'),
            'match_no': clean_text(m.group('match_no')),
            'league': league_name,
            'away_team': clean_text(m.group('away')),
            'home_team': clean_text(m.group('home')),
            'status': clean_text(m.group('status')),
            'time_or_score': clean_text(m.group('time_or_score')),
            'history_url': urljoin(BASE, m.group('history_href')),
            'odds_url': urljoin(BASE, f"/match/basketball/odds.php?MatchID={m.group('match_id')}&from=%2Flive%2F"),
        })
    return matches


def parse_odds_rows(html: str):
    rows = re.findall(r'<tr[^>]*onclick="javascript:window.location=\'([^\']+)\'"[^>]*>(.*?)</tr>', html, re.S)
    companies = []
    for href, row_html in rows:
        vals = re.findall(r'<span[^>]*>(.*?)</span>', row_html, re.S)
        vals = [clean_text(v) for v in vals if clean_text(v)]
        if len(vals) < 5:
            continue
        company = vals[0]
        nums = vals[1:5]
        companies.append({
            'company': company,
            'initial_away': nums[0],
            'initial_home': nums[1],
            'latest_away': nums[2],
            'latest_home': nums[3],
            'change_url': urljoin(BASE, href.replace('&amp;', '&')),
        })
    return companies


def parse_change_history(html: str):
    trs = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)
    history = []
    for tr in trs[2:]:
        tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
        if len(tds) < 2:
            continue
        nums = re.findall(r'<span[^>]*>(.*?)</span>', tds[0], re.S)
        nums = [clean_text(x) for x in nums if clean_text(x)]
        if len(nums) < 2:
            nums = [clean_text(x) for x in re.split(r'<br\s*/?>', tds[0]) if clean_text(x)]
        time_text = clean_text(tds[-1])
        if len(nums) >= 2 and time_text:
            history.append({
                'away': nums[0],
                'home': nums[1],
                'time': time_text,
            })
    return history


def scrape():
    live_html = fetch(LIVE_URL)
    matches = parse_live_matches(live_html)
    out = {
        'source': LIVE_URL,
        'scraped_at_epoch': int(time.time()),
        'matches': [],
    }
    for match in matches:
        odds_html = fetch(match['odds_url'], referer=match['history_url'])
        companies = parse_odds_rows(odds_html)
        match_out = match | {'moneyline_companies': companies}
        for company in match_out['moneyline_companies']:
            try:
                change_html = fetch(company['change_url'], referer=match['odds_url'])
                company['history'] = parse_change_history(change_html)
            except Exception as e:
                company['history_error'] = str(e)
            time.sleep(0.3)
        out['matches'].append(match_out)
        time.sleep(0.5)
    return out


if __name__ == '__main__':
    data = scrape()
    out_path = Path('/root/.openclaw/workspace/data/okooo_nba_odds_changes.json')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(out_path)
    print(json.dumps({
        'match_count': len(data['matches']),
        'companies_per_match': [len(m['moneyline_companies']) for m in data['matches']],
    }, ensure_ascii=False, indent=2))
