# ATGL Backtest (Alpaca)

This project implements a fast, approximate backtest of the "Above the Green Line" (ATGL) concept using Alpaca daily bars.

## What is implemented
- Green line: 250-day simple moving average of daily highs
- Relative strength: composite of 3/6/12-month returns, ranked cross-sectionally; signal requires top 10% (>= 90th percentile)
- Money Wave proxy: 14-day stochastic %K/%D with a cross-up from oversold for entry
- Exit: close below green line or stochastic cross-down from overbought

These are faithful proxies, but not the exact StockCharts SCTR or the proprietary Money Wave. If you want the exact formulas, we can swap them in.

## Quick start
1. Create a `.env` with your Alpaca keys
2. Install dependencies
3. Run the backtest

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.backtest_atgl
```

## Paper trading (live signals)
This script evaluates **current signals** and places paper orders on your Alpaca account so you can see them on the Alpaca dashboard.

Dry run (no orders submitted):
```powershell
python -m src.paper_atgl --universe dynamic --max-symbols 200
```

Live trading (submits orders):
```powershell
python -m src.paper_atgl --universe dynamic --max-symbols 200 --live
```

Notes:
- Default lookback is 600 days to compute 250-day green line and 12-month relative strength.
- Add `--min-price 5` to avoid thin/low-price stocks.
- Create a `pause_trading.txt` file to temporarily disable live orders (it will force dry-run).
- A run summary is written to `latest_summary.txt`.
- The summary includes full buy/sell lists.

## Configuration
- Universe
  - Default: a static list of very liquid US stocks and ETFs for fast results
  - Set `UNIVERSE_MODE=dynamic` and `MAX_SYMBOLS=200` to rank by 60-day average dollar volume
  - Or run `python -m src.backtest_atgl --universe dynamic --max-symbols 200`
- Data feed
  - Set `ALPACA_DATA_FEED=iex` for free data, or `sip` if your account has it
- Time window
  - Use `--years` flag, default is 3
- Slippage
  - Use `--slippage`, default is 0.0005 (0.05% per turnover)
- Trade log
  - Use `--trade-log trade_log.csv` to export trade-level entries/exits
- Email notifications
  - Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `EMAIL_FROM`, `EMAIL_TO` in `.env`
  - The scheduler runs with `--email` to send the summary after each run

## Files
- `src/backtest_atgl.py`
- `src/indicators.py`
- `src/alpaca_data.py`
- `src/universe.py`
- `src/metrics.py`
- `.env.example`

## Notes
- This backtest uses daily bars and equal-weight allocation across active signals.
- For a more realistic simulation, we can add commissions, intraday execution timing, and exact indicator definitions.
