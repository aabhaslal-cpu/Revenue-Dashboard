# Trading Sim — Round 2 🤖📈

An **autonomous daily trading simulation agent**. It manages a $100K paper
portfolio for maximum returns over 30 days (2026-06-20 → 2026-07-20). The agent
makes **every** decision itself — asset selection, sizing, entry/exit, timing.
There are no predefined positions or allocations.

> ⚠️ **Simulation only.** This is paper trading. No real orders are placed and
> no brokerage is connected. `portfolio.json` is a simulated ledger.

## What it does each day

1. **Fetches live prices** across all asset classes
   - Crypto via **CoinGecko**: BTC, ETH, SOL, HYPE, LINK, AVAX, SUI
   - Stocks via **yfinance**: NVDA, RKLB
   - ETFs via **yfinance**: SPY, QQQ, OIH, SLV, GLD, ARKK
2. **Pulls today's headlines** (NewsAPI, with free RSS fallback)
3. **Loads portfolio state** from `portfolio.json`
4. **Calls Claude** (`claude-opus-4-8`, adaptive thinking) for the trade decision
5. **Executes** the decision — updates `portfolio.json` (atomic write)
6. **Logs** everything to Notion + `history.json`
7. **Prints** a daily summary to the terminal

## File structure

```
trading-sim-r2/
  agent.py            # main orchestrator (run this)
  prices.py           # price fetcher (crypto + stocks + ETFs)
  news.py             # headline fetcher (NewsAPI + RSS fallback)
  decision_engine.py  # Claude API call + JSON parse
  notion_logger.py    # Notion integration
  utils.py            # logging, retry/backoff, atomic JSON I/O
  portfolio.json      # live portfolio state
  history.json        # full daily history log
  errors.log          # error alerts (auto-created)
  .env                # API keys (you create this — never commit it)
  .env.example        # template for .env
  requirements.txt
  README.md
```

## Setup

```bash
cd trading-sim-r2
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and add your keys
```

### Environment variables (`.env`)

| Variable             | Required | Notes |
|----------------------|----------|-------|
| `ANTHROPIC_API_KEY`  | ✅ Yes   | Claude API key (the decision engine). |
| `NOTION_API_KEY`     | optional | Notion integration token. Logging is skipped if blank. |
| `NOTION_DATABASE_ID` | optional | Target Notion database id. |
| `COINGECKO_API_KEY`  | optional | Raises crypto rate limits. Works without one. |
| `COINGECKO_API_TIER` | optional | `demo` (default) or `pro`. |
| `NEWS_API_KEY`       | optional | newsapi.org key. Falls back to RSS if blank. |

If an optional integration is unconfigured, the agent **degrades gracefully**
(skips Notion, falls back to RSS, fetches crypto on the free endpoint) and keeps
trading.

## Running

```bash
# Run one cycle immediately
python agent.py --run-now

# Backtest a specific date (simulation harness; uses latest available prices)
python agent.py --backtest --date 2026-06-20

# Start the built-in scheduler (daily run at 06:00 local time)
python agent.py
```

## Scheduling at 6am PT

The built-in scheduler (`python agent.py`) runs at **06:00 in the machine's
local time**. For reliable 6am PT execution, either set the host timezone to
`America/Los_Angeles`, or use cron (recommended for unattended servers):

```cron
# crontab -e  — 6:00 AM Pacific. Set CRON_TZ so DST is handled for you.
CRON_TZ=America/Los_Angeles
0 6 * * *  cd /path/to/trading-sim-r2 && /path/to/.venv/bin/python agent.py --run-now >> cron.out 2>&1
```

With cron you do **not** need the long-running scheduler — each day fires a
single `--run-now` cycle.

## Notion database schema

Create a database named **"Trading Sim — Round 2"** with these properties
(types matter), then share it with your integration and copy its id into
`NOTION_DATABASE_ID`:

| Property            | Type   |
|---------------------|--------|
| Date                | Title  |
| Portfolio Value     | Number |
| Daily P&L $         | Number |
| Daily P&L %         | Number |
| Cumulative P&L $    | Number |
| Cumulative P&L %    | Number |
| Cash %              | Number |
| Positions           | Text   |
| Trade Actions       | Text   |
| Market Assessment   | Text   |
| Reasoning           | Text   |
| Top Headlines       | Text   |

## Robustness / error handling

- **Retries**: every external API call retries up to 3× with exponential
  backoff (2s → 4s → 8s).
- **Partial price failures**: a failed asset is logged and skipped; the run
  continues with whatever prices succeeded.
- **Claude failure**: if the decision call fails or returns unparseable output,
  the agent **holds all positions** for the day (no trades) and logs it.
- **Atomic portfolio writes**: `portfolio.json` is written to a temp file and
  atomically renamed, so a crash mid-write never corrupts it.
- **Error alerts**: warnings and errors are appended to `errors.log`.

## How trades are executed

The agent applies the model's BUY/SELL/HOLD trades to the ledger with defensive
guards: max 5 positions, never spend more cash than available (oversized buys
are trimmed to the cash limit), and sells are capped at the held quantity. The
portfolio is then marked to market against live prices to compute P&L.
