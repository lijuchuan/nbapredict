---
name: sports-nba
description: NBA pregame betting-style prediction workflow focused on Okooo handicap evidence, Leisu lineup/injury verification, and fallback source checks. Use when predicting NBA games, preparing pregame writeups, building赛前30分钟终版分析, checking盘口/水位变化, verifying首发/伤停, generating DingTalk-ready prediction summaries, or setting recurring NBA prediction routines.
---

# Sports NBA

Use this skill for NBA pregame prediction tasks where the output should be grounded in sportsbook movement and verifiable lineup news.

## Workflow

### 1. Start with Okooo match discovery
- Use the Okooo live page to confirm the matchup and scheduled time.
- Extract the `MatchID` from the live entry.
- Treat the live page as the index, not the primary odds evidence.

Okooo live page:
- `https://m.okooo.com/live/?LotteryType=lancai`

### 2. Use Okooo handicap page as the primary盘口证据
Construct the handicap URL using the discovered `MatchID`:
- `https://m.okooo.com/match/basketball/handicap.php?Type=hwl&MatchID=<MatchID>&from=%2Flive%2F`

This page is the primary source for:
- 初始让分
- 最新让分
- 客队水位
- 主队水位
- 升盘 / 降盘
- 升水 / 降水
- 不同公司是否一致

When reading the table:
- Be careful with home/away interpretation.
- Do not assume the negative number always belongs to the left-side team without reconciling it with the page header and the 客/主 columns.
- If the direction is ambiguous, state the raw changes first and avoid overclaiming the side assignment.

### 3. Use Leisu as the primary lineup/injury source
Primary Leisu entry point:
- `https://www.leisu.com/guide/lanqiu`

Also use searchable Leisu pages and direct game pages when available.

Priority from Leisu:
1. Confirmed injury/availability notes
2. Confirmed return / absence notes
3. Confirmed starting lineup

#### 3.1 当雷速查不到时：必须继续从 NBA 官网爬取/核验
如果雷速 **查不到首发阵容** 或 **伤残/伤停情况**（包含：未展示、信息为空、只有传闻无“确认”标记），不要停在“未公布”，需要继续到 NBA 官方渠道补全/核验。

优先级（从上到下逐个尝试，命中即可停）：
1. **NBA 官方伤病报告（官方口径）**：`https://official.nba.com/`（通常在 Injury Report/下载 PDF/按日期发布）
2. **NBA 比赛页/预览页（阵容与出战状态线索）**：`https://www.nba.com/game/`（进入对应比赛页面，查看 Preview/News/Matchup/Lineups 等模块，页面结构会随赛季调整）
3. **球队官网新闻页（补充口径）**：`https://www.nba.com/team/`（球队新闻/伤病更新）

抓取/整理规则：
- **伤停**：以 NBA 官方 injury report 为准，记录球员、状态（Out/Doubtful/Questionable/Probable 等）、原因（如有）、更新时间/日期（如可见）。
- **首发**：NBA 官网未必总会“明确列出首发五人”。若能在比赛页或球队发布中找到“Starting Lineup/Starters”才可写“已确认首发”；否则只能写“暂未确认首发”，并保留已核验到的伤停信息。
- **冲突处理**：若雷速与 NBA 官网冲突，以 **NBA 官方 injury report** 为最高优先级；同时在输出里说明“雷速与 NBA 官方案例不一致，以官报为准”。

当雷速没有信息、NBA 官网也未检索到时，才允许写：
- `雷速未查到首发/伤停，NBA官网亦未检索到明确发布，暂不强写`

### 4. Use fallback sources only when the two primaries are insufficient
If Okooo handicap details or Leisu lineup/injury confirmation are missing, use fallbacks such as:
- NBA official site
- ESPN
- DraftKings odds pages
- Other public odds pages already validated in-session

Use fallback sources to fill gaps, not to replace the main structure.

### 5. Output style
Default to this structure for pregame outputs:

```text
NBA终版预测｜A vs B（赛前30分钟）
1）盘口变化结论（澳客）
• 胜负指数：若未核到，明确写暂未完整核验
• 竞彩官方胜负：若未核到，明确写暂未完整核验
• 让分盘：写初盘→最新盘、水位变化、公司分歧/一致性
• 大小分：若未核到，明确写暂未完整核验
2）阵容/伤停（雷速可验证）
• 只写已核实信息
• 若首发未出，写“雷速首发暂未公布”
3）胜负倾向
4）让分倾向
5）大小分倾向
6）参考比分
一句话结论
```

## Hard rules

- Do not fabricate盘口数字.
- Do not fabricate首发.
- Prefer raw evidence over polished but weak claims.
- If only part of the evidence is available, say so clearly.
- Distinguish between:
  - 赢球倾向
  - 让分倾向
  - 深盘是否值得追
- If market signals disagree across companies, call out the split explicitly.

## Interpretation heuristics

### When many companies deepen the same line
This usually indicates the market is reinforcing the favored side.

### When official handicap deepens but many books shallow the line
This suggests disagreement and weaker confidence in the favorite covering.

### When盘口 stays similar but one side water drops sharply
This suggests pressure or protection on that side without a full line move.

### Deep spread warning
If a side is already laying or receiving an extreme number, be careful to separate:
- favorite likely wins
- favorite likely covers

Those are not the same judgment.

## DingTalk-ready writing style
When the user wants a sendable final version:
- Keep the language crisp and market-oriented.
- Lead with evidence, not fluff.
- Use short bullets.
- End with one sentence summarizing the market read.

## References
- Read `references/template.md` when you need the standard phrasing template.
