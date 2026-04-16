"""
🦇 SILENT GUARDIAN v4 — Indicators
=====================================
v3'teki tüm göstergeler + Keltner Channel + Squeeze Detection
"""

import pandas as pd
import numpy as np


def add_ema(df, short=20, long=50):
    df = df.copy()
    df["ema_short"] = df["close"].ewm(span=short, adjust=False).mean()
    df["ema_long"] = df["close"].ewm(span=long, adjust=False).mean()
    df["trend"] = "SIDEWAYS"
    df.loc[df["ema_short"] > df["ema_long"] * 1.003, "trend"] = "UPTREND"
    df.loc[df["ema_short"] < df["ema_long"] * 0.997, "trend"] = "DOWNTREND"
    return df


def add_rsi(df, period=14):
    df = df.copy()
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df["rsi"] = 100 - (100 / (1 + rs))
    return df


def add_stochastic(df, k=14, d=3):
    df = df.copy()
    low_min = df["low"].rolling(k).min()
    high_max = df["high"].rolling(k).max()
    df["stoch_k"] = 100 * (df["close"] - low_min) / (high_max - low_min + 1e-10)
    df["stoch_d"] = df["stoch_k"].rolling(d).mean()
    return df


def add_macd(df, fast=12, slow=26, signal=9):
    df = df.copy()
    ema_f = df["close"].ewm(span=fast, adjust=False).mean()
    ema_s = df["close"].ewm(span=slow, adjust=False).mean()
    df["macd_line"] = ema_f - ema_s
    df["macd_signal"] = df["macd_line"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"] = df["macd_line"] - df["macd_signal"]
    prev = df["macd_hist"].shift(1)
    df["macd_turning_up"] = (df["macd_hist"] > prev) & (prev < 0)
    df["macd_turning_down"] = (df["macd_hist"] < prev) & (prev > 0)
    return df


def add_bollinger(df, window=20, num_std=2.0):
    df = df.copy()
    df["bb_mid"] = df["close"].rolling(window).mean()
    bb_std = df["close"].rolling(window).std()
    df["bb_upper"] = df["bb_mid"] + (num_std * bb_std)
    df["bb_lower"] = df["bb_mid"] - (num_std * bb_std)
    df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-10)
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / (df["bb_mid"] + 1e-10)
    return df


def add_keltner(df, ema_period=20, atr_mult=1.5, atr_period=10):
    """
    🆕 Keltner Channel — ATR bazlı bant.

    Bollinger'den farkı:
        Bollinger = SMA ± Standart Sapma (volatiliteye aşırı duyarlı)
        Keltner = EMA ± ATR (daha pürüzsüz, outlier'lara dirençli)

    Squeeze Tespiti:
        Bollinger bantları Keltner bantlarının İÇİNE girerse
        → Volatilite sıkışması → PATLAMA yakın!
        Bu, en güçlü momentum sinyallerinden biridir.
    """
    df = df.copy()

    # Keltner merkez
    df["kc_mid"] = df["close"].ewm(span=ema_period, adjust=False).mean()

    # ATR hesapla
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(atr_period).mean()

    df["kc_upper"] = df["kc_mid"] + (atr_mult * atr)
    df["kc_lower"] = df["kc_mid"] - (atr_mult * atr)

    # Keltner pozisyonu
    df["kc_position"] = (df["close"] - df["kc_lower"]) / (df["kc_upper"] - df["kc_lower"] + 1e-10)

    return df


def add_squeeze(df):
    """
    🆕 Bollinger-Keltner Squeeze Detection.

    BB bandı KC bandının İÇİNDEyse → squeeze aktif
    Squeeze bittiğinde → momentum patlaması beklenir
    """
    df = df.copy()

    if all(c in df.columns for c in ["bb_lower", "bb_upper", "kc_lower", "kc_upper"]):
        df["squeeze_on"] = (df["bb_lower"] > df["kc_lower"]) & (df["bb_upper"] < df["kc_upper"])
        prev_squeeze = df["squeeze_on"].shift(1).fillna(False)
        df["squeeze_fire"] = prev_squeeze & ~df["squeeze_on"]  # Squeeze bitti = ateşlendi
    else:
        df["squeeze_on"] = False
        df["squeeze_fire"] = False

    return df


def add_zscore(df, window=20):
    df = df.copy()
    rm = df["close"].rolling(window).mean()
    rs = df["close"].rolling(window).std()
    df["zscore"] = (df["close"] - rm) / (rs + 1e-10)
    return df


def add_volume_analysis(df, spike_mult=2.0, vwap_window=20):
    df = df.copy()
    df["vol_avg"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / (df["vol_avg"] + 1e-10)
    df["volume_spike"] = df["vol_ratio"] >= spike_mult

    tp = (df["high"] + df["low"] + df["close"]) / 3
    cumvol = df["volume"].rolling(vwap_window).sum()
    cumtp = (tp * df["volume"]).rolling(vwap_window).sum()
    df["vwap"] = cumtp / (cumvol + 1e-10)
    df["vwap_dev"] = ((df["close"] - df["vwap"]) / (df["vwap"] + 1e-10)) * 100

    return df


def add_atr(df, period=14):
    df = df.copy()
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(period).mean()
    df["atr_pct"] = (df["atr"] / df["close"]) * 100
    return df


def calculate_all(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Tüm göstergeleri tek seferde hesapla."""
    s = config["strategy"]

    df = add_ema(df, s["ema_short"], s["ema_long"])
    df = add_rsi(df, s["rsi_period"])
    df = add_stochastic(df, s["stoch_k"], s["stoch_d"])
    df = add_macd(df, s["macd_fast"], s["macd_slow"], s["macd_signal"])
    df = add_bollinger(df, s["bollinger_window"], s["bollinger_std"])
    df = add_keltner(df, s["keltner_ema"], s["keltner_atr_mult"], s["keltner_atr_period"])
    df = add_squeeze(df)
    df = add_zscore(df, s["zscore_window"])
    df = add_volume_analysis(df, s["volume_spike_mult"], s["vwap_window"])
    df = add_atr(df, s["atr_period"])

    return df
