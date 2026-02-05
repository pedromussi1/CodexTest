from __future__ import annotations

import os
from typing import Iterable

import requests
from dotenv import load_dotenv


class AlpacaTradingClient:
    def __init__(self) -> None:
        load_dotenv()
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.api_secret = os.getenv("ALPACA_API_SECRET")
        self.trading_url = os.getenv("ALPACA_TRADING_URL", "https://paper-api.alpaca.markets")
        if not self.api_key or not self.api_secret:
            raise ValueError("Missing ALPACA_API_KEY or ALPACA_API_SECRET in .env")

        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
        }

    def get_account(self) -> dict:
        url = f"{self.trading_url}/v2/account"
        resp = requests.get(url, headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_positions(self) -> list[dict]:
        url = f"{self.trading_url}/v2/positions"
        resp = requests.get(url, headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def submit_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = "market",
        time_in_force: str = "day",
    ) -> dict:
        url = f"{self.trading_url}/v2/orders"
        payload = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
        }
        resp = requests.post(url, headers=self.headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def cancel_all_orders(self) -> list[dict]:
        url = f"{self.trading_url}/v2/orders"
        resp = requests.delete(url, headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
