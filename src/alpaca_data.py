from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Iterable

import pandas as pd
import requests
from dotenv import load_dotenv


class AlpacaClient:
    def __init__(self) -> None:
        load_dotenv()
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.api_secret = os.getenv("ALPACA_API_SECRET")
        self.trading_url = os.getenv("ALPACA_TRADING_URL", "https://paper-api.alpaca.markets")
        self.data_url = os.getenv("ALPACA_DATA_URL", "https://data.alpaca.markets")
        self.data_feed = os.getenv("ALPACA_DATA_FEED", "iex")
        if not self.api_key or not self.api_secret:
            raise ValueError("Missing ALPACA_API_KEY or ALPACA_API_SECRET in .env")

        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
        }

    def get_assets(self) -> list[dict]:
        url = f"{self.trading_url}/v2/assets"
        params = {"status": "active", "asset_class": "us_equity"}
        resp = requests.get(url, headers=self.headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_bars(self, symbols: Iterable[str], start: datetime, end: datetime, timeframe: str = "1Day") -> pd.DataFrame:
        url = f"{self.data_url}/v2/stocks/bars"
        start_utc = start.astimezone(timezone.utc)
        end_utc = end.astimezone(timezone.utc)
        params = {
            "symbols": ",".join(symbols),
            "timeframe": timeframe,
            "start": start_utc.isoformat().replace("+00:00", "Z"),
            "end": end_utc.isoformat().replace("+00:00", "Z"),
            "adjustment": "all",
            "limit": 10000,
            "feed": self.data_feed,
        }

        all_rows: list[dict] = []
        page_token = None
        while True:
            if page_token:
                params["page_token"] = page_token
            resp = requests.get(url, headers=self.headers, params=params, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
            for sym, rows in payload.get("bars", {}).items():
                for row in rows:
                    row["symbol"] = sym
                    all_rows.append(row)
            page_token = payload.get("next_page_token")
            if not page_token:
                break

        if not all_rows:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "symbol"]).set_index(["timestamp", "symbol"])

        df = pd.DataFrame(all_rows)
        df["timestamp"] = pd.to_datetime(df["t"], utc=True)
        df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        df = df[["timestamp", "open", "high", "low", "close", "volume", "symbol"]]
        return df.set_index(["timestamp", "symbol"]).sort_index()
