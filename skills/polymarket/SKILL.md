---
name: polymarket
description: Research and analyze Polymarket prediction markets, questions, probabilities, market structure, and event framing. Use when the user asks about Polymarket markets, wants help finding or evaluating a market, comparing implied probabilities, summarizing catalysts, checking market wording/rules, or preparing trading/research notes related to Polymarket.
---

# Polymarket

Use this skill to research Polymarket markets and turn raw market information into concise decision support.

## Workflow

1. Find the relevant market page or credible references using web search.
2. Fetch readable content from the market page and supporting sources.
3. Extract the exact market question, resolution condition, current implied probability, timing, and key catalysts.
4. Cross-check with at least one non-Polymarket source when discussing likelihood or important news.
5. Separate clearly:
   - what the market says
   - what outside evidence says
   - what is still uncertain
6. If the user wants a prediction, give a probabilistic view with explicit caveats. Do not present guesses as facts.

## What to include

When useful, summarize in this order:
- Market question
- Current probability / price
- Resolution criteria / deadline
- Main bullish case
- Main bearish case
- Key risks / unknowns
- Bottom-line view

## Rules

- Quote the market wording accurately.
- If resolution wording is ambiguous, say so explicitly.
- Distinguish between market-implied probability and your own assessment.
- Prefer concise research notes over hype.
- Do not claim live prices unless you just fetched them.

## Tooling

- Use `web_search` to locate the exact Polymarket market or supporting news.
- Use `web_fetch` to read market pages, docs, news, and official sources.
- If the user asks for a reusable note or archive, save it under `reports/` or `research/` in the workspace.
