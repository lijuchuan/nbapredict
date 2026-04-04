---
name: nba-lineups-injuries-fetch
description: Fetches daily NBA starting lineups and RotoWire-side injury notes from RotoWire, plus the latest official NBA injury report PDF from the league index page, and writes merged results to a JSON file. Use when the user asks for NBA starters, lineups, injury report JSON, RotoWire lineups scrape, or official NBA injury PDF data for the current season.
---

# NBA 首发与伤停数据抓取（RotoWire + NBA 官方）

## 用途

将下列两类数据合并写入**一个 JSON 文件**：

1. **RotoWire** [NBA Daily Lineups](https://www.rotowire.com/basketball/nba-lineups.php)：当日对阵、开赛时间（ET）、客队/主队名称与战绩、每侧 **Confirmed / Expected**、首发五人（位置与姓名）、**MAY NOT PLAY** 列表（含 Out/Prob 等标签）。
2. **NBA 官方** [Injury Report 索引页](https://official.nba.com/nba-injury-report-2025-26-season/)：解析页面中指向 `ak-static.cms.nba.com` 的 PDF 链接，按文件名中的日期与时间选取**最新一份**伤病报告，下载后用 `pdfplumber` 抽取全文，并按场次切分为 `by_game` / `segments`（见下文）。

## 一键执行

在项目根目录：

```bash
pip install pdfplumber   # 官方 PDF 正文与按场切分依赖；不装则 JSON 内仅有 latest_pdf_url 与错误说明
python3 skills/nba-lineups-injuries-fetch/scripts/fetch_lineups_injuries.py
```

默认输出：`data/nba_lineups_injuries_<UTC日期>.json`。指定路径：

```bash
python3 skills/nba-lineups-injuries-fetch/scripts/fetch_lineups_injuries.py -o data/my_nba_snapshot.json
```

## JSON 结构（约定）

| 字段 | 含义 |
|------|------|
| `fetched_at_utc` | 抓取时间（UTC ISO） |
| `sources` | 两个入口 URL |
| `rotowire.games[]` | 每场：`time_et`、`away_team`/`home_team`、`away`/`home`（含 `lineup_status`、`starters`、`may_not_play`） |
| `rotowire.error` | RotoWire 拉取失败时的错误信息 |
| `nba_official.latest_pdf_url` | 当前索引页上按文件名排序得到的最新 PDF |
| `nba_official.pdf_text` | 整份 PDF 合并纯文本（便于检索） |
| `nba_official.by_game[]` | 按 `(ET) AWY@HOM` 锚点切分的大段；含 `injury_block_text` 与 `segments` |
| `nba_official.by_game[].segments[]` | 同一时间档内若出现单独一行的 `MIN@PHI` 等对阵，会再拆成多段，每段 `matchup` + `text` |
| `nba_official.pdf_parse_error` | 索引/PDF/依赖失败原因 |

## 可信度与合规

- **首发**：RotoWire 的 **Confirmed** 与 **Expected** 需区分；Expected 不得写作「官方已确认首发」。与 NBA 官网或临场消息冲突时，在分析中说明来源。
- **伤停**：**以 NBA 官方 PDF 为最高优先级**；RotoWire「MAY NOT PLAY」仅作辅助。
- 遵守站点 robots/条款与合理请求频率；本脚本为个人研究用途的小流量 GET。

## 故障与扩展

- RotoWire 若返回空或 403：可参考仓库内 [scrapling](../scrapling/SKILL.md) 用 `StealthyFetcher` 拉取同 URL，再将 HTML 交给自改脚本逻辑。
- 索引页赛季 URL 会随赛季变更：若联盟更换路径，更新脚本内 `NBA_INJURY_INDEX_URL` 与 skill 描述中的链接。

## 附加说明

- 依赖与安装见 [references/setup.md](references/setup.md)。
