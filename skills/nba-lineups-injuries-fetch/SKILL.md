---
name: nba-lineups-injuries-fetch
description: Fetches daily NBA starting lineups and side injury notes from RotoWire, structured per-team injuries from ESPN, plus the latest official NBA injury report PDF from the league index page; merges RotoWire games with ESPN injury tables by team and writes one JSON file. Use when the user asks for NBA starters, lineups, multi-source injury fusion, ESPN injuries scrape, RotoWire lineups, or official NBA injury PDF data.
---

# NBA 首发与伤停数据抓取（RotoWire + ESPN + NBA 官方）

## 用途

将下列数据**多源融合**写入**一个 JSON 文件**：

1. **RotoWire** [NBA Daily Lineups](https://www.rotowire.com/basketball/nba-lineups.php)：当日对阵、开赛时间（ET）、主客队、**Confirmed / Expected**、首发五人、**MAY NOT PLAY**。
2. **ESPN** [NBA Injuries](https://www.espn.com/nba/injuries)：30 支球队表格——球员、位置、预计回归、状态、备注（第三方汇总）。
3. **NBA 官方** [Injury Report 索引](https://official.nba.com/nba-injury-report-2025-26-season/)：最新 PDF 全文 + 按场切分的 `by_game` / `segments`。

**融合层 `merged.games[]`**：在每场 RotoWire 对阵上挂载 `injury_crosswalk`，将客、主队名对齐到 ESPN 完整队名，并附上该队 ESPN 伤病列表（队名用「末 token」匹配，避免 `Nets` 误命中 `Hornets`）。

## 一键执行

在项目根目录：

```bash
pip install pdfplumber   # 仅官方 PDF 解析需要；不装则 nba_official 仅有 PDF 链接与错误说明
python3 skills/nba-lineups-injuries-fetch/scripts/fetch_lineups_injuries.py
```

默认输出：按**北京时间**日期建子目录，文件落在其下：

`data/<YYYY-MM-DD>/nba_lineups_injuries_<YYYY-MM-DD>.json`

（例如 `data/2026-04-05/nba_lineups_injuries_2026-04-05.json`。）

JSON 内会带 `fetched_at_utc`、`fetched_at_beijing`、`archive_date_beijing`（与目录名一致的北京日历日）。

```bash
python3 skills/nba-lineups-injuries-fetch/scripts/fetch_lineups_injuries.py -o data/my_nba_snapshot.json
```

## JSON 结构（约定）

| 字段 | 含义 |
|------|------|
| `fetched_at_utc` | 抓取时间（UTC ISO） |
| `fetched_at_beijing` | 抓取时间（北京时间 ISO，含偏移） |
| `archive_date_beijing` | 归档日历日 `YYYY-MM-DD`（与 `data/` 下子目录名一致） |
| `sources` | 三个入口 URL |
| `rotowire.games[]` / `rotowire.error` | 同前 |
| `espn.teams[]` | `{ "team", "players": [{ name, position, est_return_date, status, comment }] }` |
| `espn.error` | ESPN 拉取失败信息 |
| `nba_official.*` | 同前（`latest_pdf_url`、`pdf_text`、`by_game`、`pdf_parse_error`） |
| `merged.games[]` | 每场在 RotoWire 字段基础上增加 `injury_crosswalk.away|home`：`rotowire_name`、`espn_team`、`espn_players` |
| `merged.fusion_notes_zh` | 多源优先级说明（官方 > RotoWire；ESPN 对照用） |

## 可信度与合规

- **首发**：RotoWire **Confirmed** / **Expected** 须区分表述。
- **伤停**：**以 NBA 官方 PDF 为最高优先级**；RotoWire、ESPN 均为辅助与交叉验证，冲突时以官方为准。
- 遵守各站 robots/条款与合理请求频率。

## 故障与扩展

- 若 ESPN / RotoWire 返回异常：可用 [scrapling](../scrapling/SKILL.md) 的 `StealthyFetcher` 拉取同 URL 后替换解析输入（需自行改脚本或落盘 HTML）。
- 官方索引 URL 随赛季可能变化：更新脚本内 `NBA_INJURY_INDEX_URL`。

## 附加说明

- 依赖见 [references/setup.md](references/setup.md)。
