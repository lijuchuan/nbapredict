# NBA终版模板

```text
NBA终版预测｜{team_a} vs {team_b}（赛前30分钟）

1）盘口变化结论（澳客）
• 胜负指数：{moneyline_summary}
• 竞彩官方胜负：{official_ml_summary}
• 让分盘：{spread_summary}
• 大小分：{total_summary}

2）阵容/伤停（雷速可验证）
• {injury_note_1}
• {injury_note_2}
• {lineup_note}

3）胜负倾向
• {winner_pick}

4）让分倾向
• {spread_pick}

5）大小分倾向
• {total_pick}

6）参考比分
• {score_pick}

一句话结论
• {one_line_summary}
```

## Notes
- If moneyline or total data is unavailable, say `暂未完整核验`.
- If Leisu cannot find lineup/injuries, continue checking NBA official sources; if still unavailable, say `雷速未查到首发/伤停，NBA官网亦未检索到明确发布，暂不强写`.
- If lineup is unavailable after verification, prefer `暂未确认首发（雷速未出 + NBA官网未明确发布）` over only saying `雷速首发暂未公布`.
- If side assignment from Okooo is not fully certain, state the raw movement facts first and avoid overclaiming.
