from __future__ import annotations

import os
from datetime import datetime, timedelta

import pandas as pd

from .alpaca_data import AlpacaClient


DEFAULT_UNIVERSE = [
    "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "IVV", "XLK", "XLF", "XLE",
    "XLV", "XLI", "XLY", "XLP", "XLB", "XLU", "XLRE", "XLC", "XBI", "SMH",
    "SOXX", "ARKK", "ARKQ", "ARKG", "EFA", "EEM", "IEMG", "TLT", "IEF", "HYG",
    "LQD", "GLD", "SLV", "USO", "GDX", "VNQ", "VGK", "VWO", "VIG", "VYM",
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "JPM", "UNH",
    "JNJ", "XOM", "PG", "HD", "AVGO", "LLY", "V", "MA", "COST", "MRK",
]


def get_universe() -> list[str]:
    mode = os.getenv("UNIVERSE_MODE", "static").lower()
    max_symbols = int(os.getenv("MAX_SYMBOLS", "200"))

    if mode == "static":
        return DEFAULT_UNIVERSE

    client = AlpacaClient()
    assets = client.get_assets()
    symbols = [a["symbol"] for a in assets if a.get("tradable")]

    end = datetime.utcnow()
    start = end - timedelta(days=90)

    # Use a smaller chunk to keep runtime reasonable
    top_candidates = symbols[:1500]

    rows = []
    for i in range(0, len(top_candidates), 200):
        chunk = top_candidates[i:i + 200]
        bars = client.get_bars(chunk, start=start, end=end)
        if bars.empty:
            continue
        df = bars.reset_index()
        df["dollar_volume"] = df["close"] * df["volume"]
        agg = df.groupby("symbol")["dollar_volume"].mean()
        rows.append(agg)

    if not rows:
        return DEFAULT_UNIVERSE

    combined = pd.concat(rows).groupby(level=0).mean().sort_values(ascending=False)
    return combined.head(max_symbols).index.tolist()
