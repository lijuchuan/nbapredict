---
name: sports-nba
description: NBA pregame betting-style prediction workflow focused on Okooo plus Pinnacle, bet365, and OddsPortal for odds/spread/total movement, Leisu lineup/injury verification, NBA official follow-ups, and late lineup checks via RotoWire, RotoGrinders, and NBA Stats. Use when predicting NBA games, preparing pregame writeups, building赛前30分钟终版分析, checking盘口/水位变化, verifying首发/伤停/临场阵容, generating DingTalk-ready prediction summaries, or setting recurring NBA prediction routines.
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

### 2. 盘口与赔率变化（澳客 + 国际主流，不局限于单一站点）

#### 2.1 澳客：亚洲让分盘与水位（主参考之一）
Construct the handicap URL using the discovered `MatchID`:
- `https://m.okooo.com/match/basketball/handicap.php?Type=hwl&MatchID=<MatchID>&from=%2Flive%2F`

澳客页适合抓：
- 初始让分 / 最新让分、客队水位 / 主队水位
- 升盘 / 降盘、升水 / 降水
- 多公司表内是否一致（以页面展示为准）

When reading the table:
- Be careful with home/away interpretation.
- Do not assume the negative number always belongs to the left-side team without reconciling it with the page header and the 客/主 columns.
- If the direction is ambiguous, state the raw changes first and avoid overclaiming the side assignment.

#### 2.2 Pinnacle / bet365 / OddsPortal：欧赔、让分、大小与走势（补充与交叉验证）
**赔率和水位变化不限于澳客**，应尽可能用下列站点与澳客**对照**，形成「市场在往哪边动」的结论（每处数字须标注来源，避免混书混盘）：

| 站点 | 入口（从首页进入 NBA/该场赛事即可；深链随赛季会变） | 常见用途 |
|------|------------------------------------------------------|----------|
| **Pinnacle** | `https://www.pinnacle.com/` | 让分/总分、胜负价；常作「偏 sharp」参考，适合看变盘与水位 |
| **bet365** | `https://www.bet365.com/` | 临场变盘、让分与大小；部分地区需合规访问，若打不开如实写「未核验」 |
| **OddsPortal** | `https://www.oddsportal.com/`（NBA 一般在 Basketball → USA → NBA） | **初盘→即时、历史曲线、多公司聚合**；适合复盘「何时升降水」 |

使用规则：
- **盘口记法**：欧站多为美式/小数赔率 + 整数/半点让分；澳客为亚洲盘 + 水位。**对比时先对齐主客**，再写「Pinnacle 让分从 X→Y」之类，勿把两站的正负号硬套到同一侧而不核对队名。
- **水位/赔率**：写明是「欧赔（decimal）」还是「亚洲水位」，避免把 1.91 与 0.90 混为一谈。
- **分歧**：若 Pinnacle、bet365、OddsPortal 与澳客方向不一致，在结论里**点名分歧**，不要只采信一家。
- **抓取不到**：某站无该场、地区限制或页面结构变化时，写 `该场在 <站点> 暂未核到或无法访问`，不得编造。

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

#### 3.2 临场阵容补充抓取（赛前临场、雷速或 NBA 官网仍不足时）
在**赛前 30 分钟至临场**、或雷速/NBA 官网对**首发五人**仍不清晰时，可继续从下列站点抓取/交叉核对（按常用顺序尝试，不必全开；**以能明确标注来源与可信度为先**）：

1. **RotoWire NBA Daily Lineups**：`https://www.rotowire.com/basketball/nba-lineups.php`
2. **RotoGrinders NBA Starting Lineups**：`https://rotogrinders.com/lineups/nba`
3. **NBA Stats（数据站，用于交叉验证近期首发/出场模式）**：`https://www.nba.com/stats`

临场阵容站点的使用规则：
- **可信度分层**：页面上若区分 **Confirmed / Expected**（或等价文案），只把 **Confirmed** 当作「可写进终版的强依据」；**Expected / Projected** 必须写成「预期首发（非官方确认）」，不得冒充已确认首发。
- **伤停**：第三方页面的 Out/Q 等仅作**辅助**；与 **NBA 官方 injury report** 冲突时，**始终以官报为准**，并在文中点明来源差异。
- **RotoGrinders**：若显示 `lineup not released` 等，表示该侧临场名单未释出，**不得**用 Starters 列表冒充「已公布首发」，应如实写未释出或仅保留「预期」表述。
- **NBA Stats**：多用于查**近几场首发、出场时间、阵容稳定性**等统计线索，辅助判断临场变阵风险；**不**替代当场首发名单的官方或高置信度来源。若 Stats 上无当场 lineups 模块，不要硬编五人。

输出中引用上述站点时，建议简短标注来源，例如：`RotoWire 标注 Confirmed：`、`RotoGrinders 显示未释出：`。

### 4. Use fallback sources only when the two primaries are insufficient
If Okooo handicap details or Leisu lineup/injury confirmation are missing, use fallbacks such as:
- NBA official site
- RotoWire lineups (`https://www.rotowire.com/basketball/nba-lineups.php`)
- RotoGrinders lineups (`https://rotogrinders.com/lineups/nba`)
- NBA Stats (`https://www.nba.com/stats`)
- ESPN
- Pinnacle (`https://www.pinnacle.com/`)
- bet365 (`https://www.bet365.com/`)
- OddsPortal (`https://www.oddsportal.com/`)
- DraftKings odds pages
- Other public odds pages already validated in-session

Use fallback sources to fill gaps, not to replace the main structure.

### 5. Output style
Default to this structure for pregame outputs:

```text
NBA终版预测｜A vs B（赛前30分钟）
1）盘口变化结论（澳客 + Pinnacle / bet365 / OddsPortal 等，按实核来源写）
• 胜负指数：若未核到，明确写暂未完整核验（注明来自哪几家）
• 竞彩官方胜负：若未核到，明确写暂未完整核验
• 让分盘：写初盘→最新盘、水位/赔率变化；澳客与欧站并存时分别简述或点明分歧
• 大小分：若未核到，明确写暂未完整核验；有 OddsPortal 可走勢时可补一句聚合结论
2）阵容/伤停（雷速为主，NBA 官网 + RotoWire / RotoGrinders / NBA Stats 临场补充）
• 只写已核实信息；第三方「预期」与「确认」须区分表述
• 若临场仍无确认首发：写清已查渠道（如雷速/NBA/RotoWire）及结论，避免只写一句「暂未公布」
3）胜负倾向
4）让分倾向
5）大小分倾向
6）参考比分
一句话结论
```

## Hard rules

- Do not fabricate盘口数字；跨站引用时**每条数字带站点名**（如「Pinnacle：…」「澳客：…」）。
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
