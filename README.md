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
