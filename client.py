import pandas as pd
import yaml
import yfinance as yf
import requests
from pathlib import Path
from datetime import datetime, timedelta

def load_config(path: str = None) -> dict:
    if path is None:
        # Dosya artık aynı klasörde olduğu için yolu basitleştirdik
        path = Path(__file__).resolve().parent / "config.yaml"
    with open(path) as f:
        return yaml.safe_load(f)

def fetch_alpaca(symbol: str, config: dict, timeframe: str = "1Hour", limit: int = 100) -> pd.DataFrame | None:
    try:
        headers = {
            "APCA-API-KEY-ID": config["alpaca"]["api_key"],
            "APCA-API-SECRET-KEY": config["alpaca"]["secret_key"],
        }
        end = datetime.utcnow()
        start = end - timedelta(days=60)
        url = f"{config['alpaca']['data_url']}/v2/stocks/{symbol}/bars"
        params = {"timeframe": timeframe, "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "limit": limit, "adjustment": "split", "feed": "iex"}
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code != 200: return None
        data = resp.json()
        bars = data.get("bars", [])
        if not bars: return None
        df = pd.DataFrame(bars)
        df = df.rename(columns={"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        return df[["open", "high", "low", "close", "volume"]]
    except: return None

def fetch_yfinance(symbol: str, period: str = "1mo", interval: str = "1h") -> pd.DataFrame | None:
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty: return None
        df.columns = [c.lower() for c in df.columns]
        return df[["open", "high", "low", "close", "volume"]]
    except: return None

def fetch_ticker(symbol: str, config: dict) -> pd.DataFrame | None:
    if symbol.endswith(".IS"): return fetch_yfinance(symbol)
    df = fetch_alpaca(symbol, config)
    return df if df is not None else fetch_yfinance(symbol)

def get_watchlist(config: dict) -> list[dict]:
    watchlist = []
    if config["markets"]["us"]["enabled"]:
        for sector, symbols in config["us_watchlist"].items():
            for sym in symbols: watchlist.append({"symbol": sym, "sector": sector.upper(), "market": "US"})
    return watchlist
