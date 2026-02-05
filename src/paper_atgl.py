from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
from tqdm import tqdm

from .alpaca_data import AlpacaClient
from .alpaca_trading import AlpacaTradingClient
from .indicators import sma, money_wave_up, money_wave_down, composite_relative_strength
from .universe import get_universe


def build_panel(symbols: list[str], start: datetime, end: datetime, chunk_size: int = 200) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    client = AlpacaClient()
    closes = []
    highs = []
    lows = []

    for i in tqdm(range(0, len(symbols), chunk_size), desc="Loading bars"):
        chunk = symbols[i:i + chunk_size]
        bars = client.get_bars(chunk, start=start, end=end)
        if bars.empty:
            continue

        df = bars.reset_index()
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.normalize()
        df = df.sort_values(["timestamp", "symbol"])

        close = df.pivot(index="timestamp", columns="symbol", values="close")
        high = df.pivot(index="timestamp", columns="symbol", values="high")
        low = df.pivot(index="timestamp", columns="symbol", values="low")

        closes.append(close)
        highs.append(high)
        lows.append(low)

    if not closes:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    close_df = pd.concat(closes, axis=1).sort_index()
    high_df = pd.concat(highs, axis=1).sort_index()
    low_df = pd.concat(lows, axis=1).sort_index()

    close_df = close_df.loc[:, ~close_df.columns.duplicated()]
    high_df = high_df.loc[:, ~high_df.columns.duplicated()]
    low_df = low_df.loc[:, ~low_df.columns.duplicated()]

    return close_df, high_df, low_df


def compute_signals(close_df: pd.DataFrame, high_df: pd.DataFrame, low_df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    green_line = high_df.apply(lambda s: sma(s, 250))

    rs_score = close_df.apply(composite_relative_strength)
    rs_rank = rs_score.rank(axis=1, pct=True) * 100

    mw_up = pd.DataFrame(index=close_df.index, columns=close_df.columns, dtype=bool)
    mw_down = pd.DataFrame(index=close_df.index, columns=close_df.columns, dtype=bool)
    for sym in close_df.columns:
        mw_up[sym] = money_wave_up(high_df[sym], low_df[sym], close_df[sym])
        mw_down[sym] = money_wave_down(high_df[sym], low_df[sym], close_df[sym])

    entry = (close_df > green_line) & (rs_rank >= 90) & mw_up
    exit_rule = (close_df < green_line) | mw_down

    latest = close_df.index[-1]
    return entry.loc[latest], exit_rule.loc[latest], close_df.loc[latest]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ATGL paper trading runner")
    parser.add_argument("--universe", type=str, default="dynamic", choices=["static", "dynamic"])
    parser.add_argument("--max-symbols", type=int, default=200)
    parser.add_argument("--lookback-days", type=int, default=600)
    parser.add_argument("--min-price", type=float, default=5.0)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--live", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.live:
        args.dry_run = False

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.lookback_days)

    symbols = get_universe(mode=args.universe, max_symbols=args.max_symbols)
    close_df, high_df, low_df = build_panel(symbols, start, end)

    if close_df.empty:
        print("No data returned for universe.")
        return

    entry_signal, exit_signal, latest_close = compute_signals(close_df, high_df, low_df)

    # Filter by price
    tradable = latest_close[latest_close >= args.min_price].index.tolist()
    entry_symbols = [s for s in entry_signal[entry_signal].index if s in tradable]
    exit_symbols = [s for s in exit_signal[exit_signal].index if s in tradable]

    trading = AlpacaTradingClient()
    account = trading.get_account()
    positions = trading.get_positions()

    current_positions = {p["symbol"]: p for p in positions}

    desired = set(entry_symbols)
    to_sell = [sym for sym in current_positions.keys() if sym not in desired]
    to_buy = [sym for sym in desired if sym not in current_positions]

    cash = float(account.get("cash", 0))
    buying_power = float(account.get("buying_power", cash))
    alloc = buying_power / max(len(to_buy), 1)

    print("ATGL Paper Trading Preview")
    print("--------------------------")
    print(f"Signals date: {close_df.index[-1].date()}")
    print(f"Entry signals: {len(entry_symbols)}  Exit signals: {len(exit_symbols)}")
    print(f"Positions: {len(current_positions)}  Buy: {len(to_buy)}  Sell: {len(to_sell)}")
    print(f"Cash: {cash:.2f}  Buying Power: {buying_power:.2f}  Alloc per new position: {alloc:.2f}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")

    for sym in to_sell:
        qty = int(float(current_positions[sym].get("qty", 0)))
        if qty <= 0:
            continue
        if args.dry_run:
            print(f"DRY RUN: SELL {sym} qty={qty}")
        else:
            trading.submit_order(sym, qty=qty, side="sell")
            print(f"SELL {sym} qty={qty}")

    for sym in to_buy:
        price = float(latest_close.loc[sym])
        qty = int(alloc // price)
        if qty <= 0:
            continue
        if args.dry_run:
            print(f"DRY RUN: BUY {sym} qty={qty} est_price={price:.2f}")
        else:
            trading.submit_order(sym, qty=qty, side="buy")
            print(f"BUY {sym} qty={qty} est_price={price:.2f}")


if __name__ == "__main__":
    main()
