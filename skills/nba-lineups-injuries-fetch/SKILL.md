---
name: nba-lineups-injuries-fetch
description: Fetches daily NBA starting lineups from RotoWire, per-team injuries from ESPN, latest official NBA injury PDF, and optional Okooo (m.okooo.com) NBA handicap (hwl) odds/spread change history from change.php URLs; merges lineup/injury sources and writes one JSON file. Use when the user asks for NBA starters, lineups, injury fusion, ESPN injuries, official NBA injury PDF, 澳客让分变化, 水位变化, or Okooo change.php hwl scraping.
---

# NBA 首发、伤停与可选澳客让分变化（RotoWire + ESPN + NBA 官方 + 澳客 hwl）

## 用途

将下列数据写入**一个 JSON 文件**（澳客为**可选**，需 CLI 指定 URL 或 mid）：

1. **RotoWire** [NBA Daily Lineups](https://www.rotowire.com/basketball/nba-lineups.php)：对阵、**Confirmed / Expected**、首发、`MAY NOT PLAY`。
2. **ESPN** [NBA Injuries](https://www.espn.com/nba/injuries)：30 队伤病表。
3. **NBA 官方** [Injury Report 索引](https://official.nba.com/nba-injury-report-2025-26-season/)：最新伤病 PDF 与按场切分文本。
4. **澳客 m 站** 篮球让分盘 **变化列表**：`change.php?...&Type=hwl` —— 抓取**盘口（line）与左右列水位/赔率**随时间的变化记录。  
   - **不能只靠队名打开变化页**：该页必须带比赛 **`mid`**。  
   - **可以不手写 URL**：提供 **客队 / 主队中文关键词**（与 live 页展示一致或子串即可），脚本会拉取 `live/?LotteryType=lancai`，在 **NBA** 条目中匹配出 `match_id`，再自动拼变化页 URL。  
   - 示例 URL：  
     `https://m.okooo.com/match/basketball/change.php?mid=5378517&pid=3&Type=hwl&c=1`  
   - 不同 `pid` 为不同博彩公司；**部分 pid 下表格可能为空**，可改用 `pid=2`（竞彩官方）等。

**融合层 `merged.games[]`**：RotoWire 每场 + ESPN 伤病对齐（`injury_crosswalk`）。

## 一键执行

在项目根目录：

```bash
pip install pdfplumber   # 仅官方 PDF 解析需要
python3 skills/nba-lineups-injuries-fetch/scripts/fetch_lineups_injuries.py
```

带**澳客让分变化**（任选一种方式）：

```bash
# 完整 URL（可多次传入不同公司/场次）
python3 skills/nba-lineups-injuries-fetch/scripts/fetch_lineups_injuries.py \
  --okooo-hwl-change-url 'https://m.okooo.com/match/basketball/change.php?mid=5378517&pid=3&Type=hwl&c=1'

# 仅填 mid，按默认 pid=3 拼 URL；无数据时改 --okooo-hwl-pid 2 等
python3 skills/nba-lineups-injuries-fetch/scripts/fetch_lineups_injuries.py \
  --okooo-mid 5378517 --okooo-hwl-pid 2

# 不传变化页 URL：用 live 页 NBA 列表 + 主客中文关键词解析 mid，再抓让分变化
python3 skills/nba-lineups-injuries-fetch/scripts/fetch_lineups_injuries.py \
  --okooo-live-away-cn 森林狼 --okooo-live-home-cn 76人 --okooo-hwl-pid 2
```

**落盘规则（固定）**：所有抓取结果一律写入仓库根目录下的 **`data/<北京时间 YYYY-MM-DD>/`**，与日历日一一对应。

- 不设 `-o`：默认文件名为 `nba_lineups_injuries_<YYYY-MM-DD>.json`（仍在上述日期子目录内）。
- 设 `-o`：只写**相对「当日归档目录」**的文件名或子路径（勿写绝对路径；若误写则只取文件名放入当日目录）。

示例：

```bash
# 写入 data/2026-04-05/nba_lineups_injuries_2026-04-05.json
python3 skills/nba-lineups-injuries-fetch/scripts/fetch_lineups_injuries.py

# 写入 data/2026-04-05/my_nba_snapshot.json
python3 skills/nba-lineups-injuries-fetch/scripts/fetch_lineups_injuries.py -o my_nba_snapshot.json

# 写入 data/2026-04-05/lineups/run1.json
python3 skills/nba-lineups-injuries-fetch/scripts/fetch_lineups_injuries.py -o lineups/run1.json
```

## JSON 结构（约定）

| 字段 | 含义 |
|------|------|
| `fetched_at_utc` / `fetched_at_beijing` / `archive_date_beijing` | 抓取与归档日（北京日历日同 `data/` 下子目录名） |
| `output_path` | 本次写入的相对路径（形如 `data/<日期>/…`） |
| `output_storage_note_zh` | 落盘目录约定说明 |
| `sources` | RotoWire / NBA 官方 / ESPN 入口 URL |
| `rotowire.*` / `espn.*` / `nba_official.*` / `merged.*` | 同前 |
| `okooo_hwl_change.fetches[]` | 每次抓取：`url`、`query`、`page_title`、`book_name_zh`、`changes[]`（`left`/`line`/`right`/`time`）、`error`；无行时可有 `empty_notice_zh` |
| `okooo_hwl_change.team_lookup` | 使用 `--okooo-live-away-cn` / `--okooo-live-home-cn` 时：live 地址、`nba_games`、`match_id`、`resolved_hwl_change_url`、`candidates`、`swapped`、`ambiguous`、`error` 等 |
| `okooo_hwl_change.interpretation_zh` | 字段含义说明（左右列与让分、时间文案） |
| `okooo_hwl_change.skipped_zh` | 未传澳客参数时说明已跳过 |

## 可信度与合规

- **首发**：RotoWire Confirmed / Expected 须区分。
- **伤停**：以 **NBA 官方 PDF** 为最高优先级；RotoWire、ESPN 为辅助。
- **澳客盘口**：数字以页面为准；左右列主客解读须对照当场队名，避免跨页误读。
- 遵守各站 robots/条款与合理请求频率。

## 故障与扩展

- 澳客需 **GBK** 解码与 **Referer**（脚本已带）；若 403/空表可试 [scrapling](../scrapling/SKILL.md) 的 `Fetcher`/`StealthyFetcher` 拉取同 URL 后接入解析函数。
- 官方索引 URL 随赛季可能变化：更新脚本内 `NBA_INJURY_INDEX_URL`。

## 附加说明

- 依赖见 [references/setup.md](references/setup.md)。
