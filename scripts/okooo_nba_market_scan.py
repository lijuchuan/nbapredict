#!/root/.openclaw/workspace/.venvs/scrapling/bin/python
import re
import json
from urllib.parse import urljoin
from collections import defaultdict

from scrapling.fetchers import Fetcher

BASE = 'https://m.okooo.com'
HEADERS = {'Referer': 'https://m.okooo.com/live/?LotteryType=lancai'}

TEAM_MAP = {
    'LA Clippers': 'Clippers', 'Milwaukee Bucks': 'Bucks', 'Miami Heat': 'Heat', 'Indiana Pacers': 'Pacers',
    'Sacramento Kings': 'Kings', 'Brooklyn Nets': 'Nets', 'Boston Celtics': 'Celtics', 'Charlotte Hornets': 'Hornets',
    'Orlando Magic': 'Magic', 'Toronto Raptors': 'Raptors', 'Washington Wizards': 'Wizards', 'Portland Trail Blazers': 'Trail Blazers',
    'Houston Rockets': 'Rockets', 'New Orleans Pelicans': 'Pelicans', 'New York Knicks': 'Knicks', 'Oklahoma City Thunder': 'Thunder',
    'Golden State Warriors': 'Warriors', 'Denver Nuggets': 'Nuggets'
}


def fetch_text(url):
    r = Fetcher.get(url, follow_redirects=True, timeout=30, stealthy_headers=True, headers=HEADERS)
    return r.text


def fetch_gbk(url):
    raw = fetch_text(url)
    if isinstance(raw, bytes):
        return raw.decode('gbk', 'ignore')
    # scrapling already decoded; if mojibake not present this is fine
    return raw


def parse_live(match_date='2026-03-29'):
    html = fetch_gbk('https://m.okooo.com/live/?LotteryType=lancai')
    ids = re.findall(r'/match/basketball/history\.php\?LotteryType=SportteryWL&MatchID=(\d+)&from=%2Flive%2F', html)
    names = re.findall(r'<p class="name fl txtright">([^<]+)', html)
    left_right = re.findall(r'<p class="name fl txtright">([^<]+).*?<span class="bifentxt gray9" id="score_(\d+)">(\d{2}:\d{2})</span>.*?<p class="name fl txtleft">([^<]+)</p>', html, re.S)
    games = []
    for away, mid, tm, home in left_right:
        if tm in {'03:30','05:00','06:00','07:00','07:30','10:00'}:
            games.append({'match_id': mid, 'away_cn': away.strip(), 'home_cn': home.strip(), 'time_bj': tm})
    return games


def parse_odds_page(mid, kind='Odds'):
    if kind == 'Odds':
        url = f'{BASE}/match/basketball/odds.php?MatchID={mid}&from=%2Flive%2F'
    elif kind == 'hwl':
        url = f'{BASE}/match/basketball/handicap.php?Type=hwl&MatchID={mid}&from=%2Flive%2F'
    else:
        url = f'{BASE}/match/basketball/handicap.php?Type=bs&MatchID={mid}&from=%2Flive%2F'
    html = fetch_gbk(url)
    title = re.search(r'<title>(.*?)</title>', html)
    title = title.group(1) if title else ''
    rows = []
    if kind == 'Odds':
        pat = re.compile(r"onclick=\"javascript:window.location='([^']+change\.php\?[^']+)'\".*?<td class=\" border_r\"><span class=\"sjwindth\">(.*?)</span></td>.*?<td class=\"datetxt02\"><span>(.*?)</span></td>.*?<td class=\"datetxt02 border_r\"><span>(.*?)</span></td>.*?<td class=\"datetxt02\"><span ?[^>]*>(.*?)</span></td>.*?<td class=\"datetxt02\"><span[^>]*>(.*?)</span></td>", re.S)
        for change_url, book, o1, o2, l1, l2 in pat.findall(html):
            rows.append({'book': book.strip(), 'open_away': o1, 'open_home': o2, 'latest_away': l1, 'latest_home': l2, 'change_url': urljoin(BASE, change_url)})
    else:
        pat = re.compile(r"onclick=\"javascript:window.location='([^']+change\.php\?[^']+)'\".*?<td class=\" border_r\"><span class=\"sjwindth\">(.*?)</span></td>.*?<td class=\"datetxt02\"><span>(.*?)</span></td>.*?<td class=\"datetxt02\"><span>(.*?)</span></td>.*?<td class=\"datetxt02 border_r\"><span>(.*?)</span></td>.*?<td class=\"datetxt02\"><span>(.*?)</span></td>.*?<td class=\"datetxt02\"><span>(.*?)</span></td>.*?<td class=\"datetxt02\"><span[^>]*>(.*?)</span></td>", re.S)
        for change_url, book, o_a, o_h, o_line, l_a, l_h, l_line in pat.findall(html):
            rows.append({'book': book.strip(), 'open_away_odds': o_a, 'open_home_odds': o_h, 'open_line': o_line, 'latest_away_odds': l_a, 'latest_home_odds': l_h, 'latest_line': l_line, 'change_url': urljoin(BASE, change_url)})
    return title, rows


def parse_change_table(url):
    html = fetch_gbk(url)
    rows = re.findall(r'<tr>\s*<td><span[^>]*>(.*?)</span><span style="width:48px;" ?>(.*?)</span><span[^>]*>(.*?)</span></td>\s*<td class="timetd">(.*?)</td>\s*</tr>', html, re.S)
    return [{'left': a.strip(), 'line': b.strip(), 'right': c.strip(), 'time': t.strip()} for a, b, c, t in rows]


def parse_rotowire_lineups():
    html = fetch_text('https://www.rotowire.com/basketball/nba-lineups.php')
    parts = html.split('<div class="lineup is-nba"')[1:]
    games = []
    for sec in parts:
        abbrs = re.findall(r'<div class="lineup__abbr">(.*?)</div>', sec)
        teams = re.findall(r'class="lineup__mteam [^"]+">\s*([A-Za-z .\'-]+)\s*<span class="lineup__wl">\(([^)]*)\)</span>', sec)
        lists = re.findall(r'<ul class="lineup__list is-(visit|home)">(.*?)</ul>', sec, re.S)
        if len(teams) < 2 or len(lists) < 2:
            continue
        game = {'away_team': teams[0][0].strip(), 'home_team': teams[1][0].strip(), 'away_record': teams[0][1], 'home_record': teams[1][1]}
        for side, ul in lists[:2]:
            starters = re.findall(r'<div class="lineup__pos"[^>]*>(.*?)</div>\s*<a[^>]*title="([^"]+)"', ul, re.S)
            inj = re.findall(r'<div class="lineup__pos"[^>]*>(.*?)</div>\s*<a[^>]*title="([^"]+)"[^>]*>.*?<span class="lineup__inj">([^<]+)</span>', ul, re.S)
            game[f'{side}_starters'] = [name for _, name in starters[:5]]
            game[f'{side}_inj'] = [{'pos': pos.strip(), 'name': name.strip(), 'tag': tag.strip()} for pos, name, tag in inj]
        games.append(game)
    return games


def parse_espn_injuries():
    team_names = ['Atlanta Hawks','Boston Celtics','Brooklyn Nets','Charlotte Hornets','Chicago Bulls','Cleveland Cavaliers','Dallas Mavericks','Detroit Pistons','Golden State Warriors','Houston Rockets','Indiana Pacers','LA Clippers','Los Angeles Lakers','Memphis Grizzlies','Miami Heat','Milwaukee Bucks','Minnesota Timberwolves','New Orleans Pelicans','New York Knicks','Oklahoma City Thunder','Orlando Magic','Philadelphia 76ers','Phoenix Suns','Portland Trail Blazers','Sacramento Kings','San Antonio Spurs','Toronto Raptors','Utah Jazz','Washington Wizards','Denver Nuggets']
    text = Fetcher.get('https://www.espn.com/nba/injuries', follow_redirects=True, timeout=30).get_all_text(separator=' ')
    teams = defaultdict(str)
    starts = []
    for team in team_names:
        idx = text.find(team)
        if idx != -1:
            starts.append((idx, team))
    starts.sort()
    for i, (idx, team) in enumerate(starts):
        nxt = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        teams[team] = text[idx:nxt]
    return teams


def main():
    live_games = parse_live()
    rw = parse_rotowire_lineups()
    inj = parse_espn_injuries()
    out = []
    for g in live_games:
        title_odds, odds_rows = parse_odds_page(g['match_id'], 'Odds')
        title_hwl, hwl_rows = parse_odds_page(g['match_id'], 'hwl')
        title_bs, bs_rows = parse_odds_page(g['match_id'], 'bs')
        # selected books
        books = ['99家平均','威廉.希尔','立博','bwin','伟德国际','Unibet','必发','竞彩官方']
        odds_sel = [r for r in odds_rows if r['book'] in books][:6]
        hwl_sel = [r for r in hwl_rows if r['book'] in ['竞彩官方','bwin']]
        bs_sel = [r for r in bs_rows if r['book'] in ['竞彩官方','bwin']]
        # line movements from first selected if any
        hwl_change = parse_change_table(hwl_sel[0]['change_url'])[:8] if hwl_sel else []
        bs_change = parse_change_table(bs_sel[0]['change_url'])[:8] if bs_sel else []
        lineup = next((x for x in rw if x['away_team'] in title_odds and x['home_team'] in title_odds), None)
        out.append({
            'match_id': g['match_id'], 'time_bj': g['time_bj'], 'title': title_odds,
            'odds': odds_sel, 'handicap': hwl_sel, 'total': bs_sel,
            'handicap_changes': hwl_change, 'total_changes': bs_change,
            'lineup': lineup,
            'injuries': {k: inj.get(k, '')[:500] for k in inj.keys() if (lineup and (k.endswith(lineup['away_team']) or k.endswith(lineup['home_team']) or k == ('LA Clippers' if lineup['away_team']=='Clippers' else '')))}
        })
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
