from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta

import pandas as pd
from tqdm import tqdm

from .alpaca_data import AlpacaClient
from .indicators import sma, money_wave_up, money_wave_down, composite_relative_strength
from .metrics import summary_stats
from .universe import get_universe


DATA_CACHE = os.path.join(os.path.dirname(__file__), "..", "data_cache")


def load_or_fetch_symbol(client: AlpacaClient, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    os.makedirs(DATA_CACHE, exist_ok=True)
    cache_path = os.path.join(DATA_CACHE, f"{symbol}.csv.gz")

    if os.path.exists(cache_path):
        df = pd.read_csv(cache_path, parse_dates=["timestamp"])
        df = df.set_index("timestamp").sort_index()
        if df.index.min() <= pd.Timestamp(start, tz="UTC") and df.index.max() >= pd.Timestamp(end, tz="UTC"):
            return df

    bars = client.get_bars([symbol], start=start, end=end)
    if bars.empty:
        return bars

    df = bars.reset_index()
    df = df[df["symbol"] == symbol]
    df = df.set_index("timestamp").sort_index()
    df.to_csv(cache_path, compression="gzip")
    return df


def build_panel(symbols: list[str], start: datetime, end: datetime) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    client = AlpacaClient()

    closes = []
    highs = []
    lows = []

    for symbol in tqdm(symbols, desc="Loading bars"):
        df = load_or_fetch_symbol(client, symbol, start, end)
        if df.empty:
            continue
        daily = df.copy()
        daily.index = daily.index.tz_convert("UTC").normalize()
        closes.append(daily["close"].rename(symbol))
        highs.append(daily["high"].rename(symbol))
        lows.append(daily["low"].rename(symbol))

    close_df = pd.concat(closes, axis=1).sort_index()
    high_df = pd.concat(highs, axis=1).sort_index()
    low_df = pd.concat(lows, axis=1).sort_index()

    return close_df, high_df, low_df


def backtest(close_df: pd.DataFrame, high_df: pd.DataFrame, low_df: pd.DataFrame, initial_capital: float, slippage: float) -> dict:
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

    positions = pd.DataFrame(0, index=close_df.index, columns=close_df.columns, dtype=int)
    for sym in close_df.columns:
        in_pos = False
        for dt in close_df.index:
            if not in_pos and bool(entry.loc[dt, sym]):
                in_pos = True
            elif in_pos and bool(exit_rule.loc[dt, sym]):
                in_pos = False
            positions.loc[dt, sym] = 1 if in_pos else 0

    daily_returns = close_df.pct_change().fillna(0.0)
    weights = positions.div(positions.sum(axis=1), axis=0).fillna(0.0)

    turnover = weights.diff().abs().sum(axis=1).fillna(0.0)
    cost = turnover * slippage

    portfolio_returns = (weights.shift(1).fillna(0.0) * daily_returns).sum(axis=1) - cost
    equity = (1 + portfolio_returns).cumprod() * initial_capital

    stats = summary_stats(equity, portfolio_returns)

    return {
        "equity": equity,
        "returns": portfolio_returns,
        "stats": stats,
        "positions": positions,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ATGL backtest (approximation)")
    parser.add_argument("--capital", type=float, default=100000.0)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--slippage", type=float, default=0.0005)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    end = datetime.utcnow()
    start = end - timedelta(days=365 * args.years)

    symbols = get_universe()
    close_df, high_df, low_df = build_panel(symbols, start, end)

    result = backtest(close_df, high_df, low_df, args.capital, args.slippage)

    stats = result["stats"]
    print("ATGL Backtest Summary")
    print("---------------------")
    print(f"Symbols: {len(close_df.columns)}")
    print(f"Start: {close_df.index.min().date()}  End: {close_df.index.max().date()}")
    print(f"Total Return: {stats['total_return']:.2%}")
    print(f"CAGR: {stats['cagr']:.2%}")
    print(f"Volatility: {stats['volatility']:.2%}")
    print(f"Sharpe: {stats['sharpe']:.2f}")
    print(f"Max Drawdown: {stats['max_drawdown']:.2%}")


if __name__ == "__main__":
    main()
