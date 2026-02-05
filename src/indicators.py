from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k: int = 14, d: int = 3) -> tuple[pd.Series, pd.Series]:
    lowest_low = low.rolling(window=k, min_periods=k).min()
    highest_high = high.rolling(window=k, min_periods=k).max()
    k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d_percent = k_percent.rolling(window=d, min_periods=d).mean()
    return k_percent, d_percent


def money_wave_up(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    k, d = stochastic(high, low, close, k=14, d=3)
    cross_up = (k > d) & (k.shift(1) <= d.shift(1))
    oversold = k.shift(1) < 20
    return cross_up & oversold


def money_wave_down(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    k, d = stochastic(high, low, close, k=14, d=3)
    cross_down = (k < d) & (k.shift(1) >= d.shift(1))
    overbought = k.shift(1) > 80
    return cross_down & overbought


def composite_relative_strength(close: pd.Series) -> pd.Series:
    r3 = close.pct_change(63)
    r6 = close.pct_change(126)
    r12 = close.pct_change(252)
    return 0.4 * r3 + 0.2 * r6 + 0.4 * r12
