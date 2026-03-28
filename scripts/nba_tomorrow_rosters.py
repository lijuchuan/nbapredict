#!/usr/bin/env python3
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

SCHEDULE_URL = 'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json'
BJ_DATE = '2026-03-29'

TEAM_INFO = {
    'Spurs': {'id': 1610612759, 'slug': 'spurs'},
    'Bucks': {'id': 1610612749, 'slug': 'bucks'},
    '76ers': {'id': 1610612755, 'slug': 'sixers'},
    'Hornets': {'id': 1610612766, 'slug': 'hornets'},
    'Kings': {'id': 1610612758, 'slug': 'kings'},
    'Hawks': {'id': 1610612737, 'slug': 'hawks'},
    'Bulls': {'id': 1610612741, 'slug': 'bulls'},
    'Grizzlies': {'id': 1610612763, 'slug': 'grizzlies'},
    'Pistons': {'id': 1610612765, 'slug': 'pistons'},
    'Timberwolves': {'id': 1610612750, 'slug': 'timberwolves'},
    'Jazz': {'id': 1610612762, 'slug': 'jazz'},
    'Suns': {'id': 1610612756, 'slug': 'suns'},
}

HEADERS = {'User-Agent': 'Mozilla/5.0'}


def get_bj_games(target_bj_date: str):
    data = requests.get(SCHEDULE_URL, headers=HEADERS, timeout=20).json()
    beijing = ZoneInfo('Asia/Shanghai')
    out = []
    for gd in data['leagueSchedule']['gameDates']:
        for g in gd['games']:
            t = datetime.fromisoformat(g['gameDateTimeUTC'].replace('Z', '+00:00')).astimezone(beijing)
            if t.date().isoformat() == target_bj_date:
                out.append({
                    'time_bj': t.strftime('%m-%d %H:%M'),
                    'away': g['awayTeam']['teamName'],
                    'home': g['homeTeam']['teamName'],
                })
    out.sort(key=lambda x: x['time_bj'])
    return out


def fetch_roster(team_name):
    info = TEAM_INFO[team_name]
    url = f"https://www.nba.com/team/{info['id']}/{info['slug']}"
    html = requests.get(url, headers=HEADERS, timeout=20).text
    matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    if not matches:
        raise RuntimeError(f'ld+json not found for {team_name}')
    obj = None
    for chunk in matches:
        try:
            cand = json.loads(chunk)
        except Exception:
            continue
        if isinstance(cand, dict) and cand.get('@type') == 'SportsTeam' and cand.get('athlete'):
            obj = cand
            break
    if not obj:
        raise RuntimeError(f'sports team json not found for {team_name}')
    names = [p['name'] for p in obj.get('athlete', []) if isinstance(p, dict) and p.get('name')]
    return names, url


def build_message(target_bj_date: str):
    games = get_bj_games(target_bj_date)
    teams = []
    for g in games:
        for tn in (g['away'], g['home']):
            if tn not in teams:
                teams.append(tn)

    rosters = {}
    for team in teams:
        names, _ = fetch_roster(team)
        rosters[team] = names

    lines = []
    lines.append(f'NBA官网抓取｜北京时间{int(target_bj_date[5:7])}月{int(target_bj_date[8:10])}日赛程与球队名单')
    lines.append('')
    for i, g in enumerate(games, 1):
        away = g['away']
        home = g['home']
        lines.append(f"{i}. {g['time_bj']} {away} vs {home}")
        lines.append(f"- {away}：{'、'.join(rosters[away])}")
        lines.append(f"- {home}：{'、'.join(rosters[home])}")
        lines.append('')
    lines.append('说明：名单来自各队 NBA 官网 Team Info / roster 数据，临场激活、伤停、轮休请以赛前官方更新为准。')
    return '\n'.join(lines)


if __name__ == '__main__':
    print(build_message(BJ_DATE))
