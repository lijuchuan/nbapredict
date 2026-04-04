# 依赖与环境

## 必选（标准库）

脚本核心 HTTP 与 JSON 仅依赖 Python 3.9+ 标准库。

## 可选：NBA 官方 PDF 结构化解析

从 [NBA 官方伤病报告页](https://official.nba.com/nba-injury-report-2025-26-season/) 下载的报表为 PDF。要提取正文并做行级解析，需要安装：

```bash
pip install pdfplumber
```

未安装时，脚本仍会在 JSON 中写入 `nba_official.latest_pdf_url` 与 `nba_official.pdf_parse_error`，便于稍后补装依赖再跑。

## RotoWire

页面为服务端渲染 HTML，一般无需浏览器。若遇 403/空页面，可改用项目内 [scrapling](../../scrapling/SKILL.md) 的 `StealthyFetcher` 拉取同一 URL。

当前仓库脚本默认使用 `urllib` + 常见浏览器 `User-Agent`。

## ESPN Injuries

`https://www.espn.com/nba/injuries` 为表格 HTML，脚本解析 `ResponsiveTable Table__league-injuries` 块，**无需额外 Python 依赖**。若页面改版导致 class 名变化，需同步更新 `parse_espn_injuries_page`。

## 澳客 m 站（让分 hwl 变化页）

- URL 形态：`https://m.okooo.com/match/basketball/change.php?mid=<比赛ID>&pid=<公司ID>&Type=hwl&c=1`
- 响应编码多为 **GBK**；建议请求头带 `Referer: https://m.okooo.com/live/?LotteryType=lancai`（脚本已加）。
- 变化行位于 `table.changeTable` 内；若某 `pid` 下表格为空，换 handicap 页上其它公司的变化链接即可。
- **队名 → mid**：变化页本身不支持按队名查询；脚本可选拉取 `live/?LotteryType=lancai`，用 `league_name == NBA` 的条目解析 `match_id`，再用主客中文关键词匹配（见 `--okooo-live-away-cn` / `--okooo-live-home-cn`）。当日 live 无 NBA 时无法匹配。
