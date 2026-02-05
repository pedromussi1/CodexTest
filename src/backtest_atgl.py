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


def backtest(
    close_df: pd.DataFrame,
    high_df: pd.DataFrame,
    low_df: pd.DataFrame,
    initial_capital: float,
    slippage: float,
    trade_log_path: str | None = None,
) -> dict:
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
    trades: list[dict] = []
    for sym in close_df.columns:
        in_pos = False
        entry_date = None
        entry_price = None
        for dt in close_df.index:
            if not in_pos and bool(entry.loc[dt, sym]):
                in_pos = True
                entry_date = dt
                entry_price = float(close_df.loc[dt, sym])
            elif in_pos and bool(exit_rule.loc[dt, sym]):
                in_pos = False
                exit_price = float(close_df.loc[dt, sym])
                below_green = bool(close_df.loc[dt, sym] < green_line.loc[dt, sym])
                mw_down_hit = bool(mw_down.loc[dt, sym])
                if below_green and mw_down_hit:
                    exit_reason = "BelowGreenLine+MoneyWaveDown"
                elif below_green:
                    exit_reason = "BelowGreenLine"
                else:
                    exit_reason = "MoneyWaveDown"

                trades.append(
                    {
                        "symbol": sym,
                        "entry_date": entry_date,
                        "entry_price": entry_price,
                        "exit_date": dt,
                        "exit_price": exit_price,
                        "return_pct": (exit_price / entry_price - 1.0) if entry_price else None,
                        "bars_held": (dt - entry_date).days if entry_date else None,
                        "exit_reason": exit_reason,
                    }
                )
                entry_date = None
                entry_price = None
            positions.loc[dt, sym] = 1 if in_pos else 0

        if in_pos and entry_date is not None and entry_price is not None:
            dt = close_df.index[-1]
            exit_price = float(close_df.loc[dt, sym])
            trades.append(
                {
                    "symbol": sym,
                    "entry_date": entry_date,
                    "entry_price": entry_price,
                    "exit_date": dt,
                    "exit_price": exit_price,
                    "return_pct": (exit_price / entry_price - 1.0),
                    "bars_held": (dt - entry_date).days,
                    "exit_reason": "EndOfTest",
                }
            )

    daily_returns = close_df.pct_change().fillna(0.0)
    weights = positions.div(positions.sum(axis=1), axis=0).fillna(0.0)

    turnover = weights.diff().abs().sum(axis=1).fillna(0.0)
    cost = turnover * slippage

    portfolio_returns = (weights.shift(1).fillna(0.0) * daily_returns).sum(axis=1) - cost
    equity = (1 + portfolio_returns).cumprod() * initial_capital

    stats = summary_stats(equity, portfolio_returns)

    if trade_log_path:
        trade_df = pd.DataFrame(trades)
        if not trade_df.empty:
            trade_df = trade_df.sort_values(["entry_date", "symbol"])
        trade_df.to_csv(trade_log_path, index=False)

    return {
        "equity": equity,
        "returns": portfolio_returns,
        "stats": stats,
        "positions": positions,
        "trades": trades,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ATGL backtest (approximation)")
    parser.add_argument("--capital", type=float, default=100000.0)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--universe", type=str, default="static", choices=["static", "dynamic"])
    parser.add_argument("--max-symbols", type=int, default=200)
    parser.add_argument("--trade-log", type=str, default="trade_log.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    end = datetime.utcnow()
    start = end - timedelta(days=365 * args.years)

    symbols = get_universe(mode=args.universe, max_symbols=args.max_symbols)
    close_df, high_df, low_df = build_panel(symbols, start, end)

    trade_log_path = args.trade_log if args.trade_log else None
    result = backtest(close_df, high_df, low_df, args.capital, args.slippage, trade_log_path=trade_log_path)

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
