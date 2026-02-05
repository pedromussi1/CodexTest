from __future__ import annotations

import numpy as np
import pandas as pd


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    drawdown = (equity / peak) - 1
    return drawdown.min()


def sharpe(returns: pd.Series, rf: float = 0.0) -> float:
    if returns.std() == 0:
        return 0.0
    excess = returns - rf / 252
    return np.sqrt(252) * excess.mean() / excess.std()


def summary_stats(equity: pd.Series, returns: pd.Series) -> dict:
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else 0.0
    vol = returns.std() * np.sqrt(252)
    stats = {
        "total_return": total_return,
        "cagr": cagr,
        "volatility": vol,
        "sharpe": sharpe(returns),
        "max_drawdown": max_drawdown(equity),
    }
    return stats
