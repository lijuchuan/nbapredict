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
