"""
🦇 SILENT GUARDIAN v4 — Scoring Engine
========================================
Ağırlıklı skor (0-100) + Keltner + Squeeze bonus
"""

import pandas as pd


def _score(value, max_score, conditions):
    """Koşulları sırayla kontrol et, ilk eşleşeni döndür."""
    for check_fn, pct, direction in conditions:
        if check_fn(value):
            return max_score * pct, direction
    return 0, "NEUTRAL"


def score_bollinger(row, w):
    bp = row.get("bb_position", 0.5)
    if bp <= 0:     return w, "BUY"
    if bp <= 0.1:   return w * 0.75, "BUY"
    if bp >= 1.0:   return w, "SELL"
    if bp >= 0.9:   return w * 0.75, "SELL"
    return 0, "NEUTRAL"


def score_keltner(row, w):
    kp = row.get("kc_position", 0.5)
    if kp <= 0:     return w, "BUY"
    if kp <= 0.1:   return w * 0.7, "BUY"
    if kp >= 1.0:   return w, "SELL"
    if kp >= 0.9:   return w * 0.7, "SELL"
    return 0, "NEUTRAL"


def score_zscore(row, w):
    z = abs(row.get("zscore", 0))
    d = "BUY" if row.get("zscore", 0) < 0 else "SELL"
    if z >= 3:   return w, d
    if z >= 2:   return w * 0.75, d
    if z >= 1.5: return w * 0.3, d
    return 0, "NEUTRAL"


def score_rsi(row, w, cfg):
    rsi = row.get("rsi", 50)
    if rsi <= 20:                    return w, "BUY"
    if rsi <= cfg["rsi_oversold"]:   return w * 0.7, "BUY"
    if rsi >= 80:                    return w, "SELL"
    if rsi >= cfg["rsi_overbought"]: return w * 0.7, "SELL"
    return 0, "NEUTRAL"


def score_stochastic(row, w, cfg):
    k, d = row.get("stoch_k", 50), row.get("stoch_d", 50)
    if k <= cfg["stoch_oversold"] and k > d:   return w, "BUY"
    if k <= cfg["stoch_oversold"]:             return w * 0.6, "BUY"
    if k >= cfg["stoch_overbought"] and k < d: return w, "SELL"
    if k >= cfg["stoch_overbought"]:           return w * 0.6, "SELL"
    return 0, "NEUTRAL"


def score_volume(row, w):
    if not row.get("volume_spike", False): return 0, "NEUTRAL"
    z = row.get("zscore", 0)
    vr = row.get("vol_ratio", 1)
    mult = 1.0 if vr >= 3 else 0.7
    d = "BUY" if z < 0 else ("SELL" if z > 0 else "NEUTRAL")
    return w * mult, d


def score_vwap(row, w):
    dev = row.get("vwap_dev", 0)
    if dev <= -2: return w, "BUY"
    if dev <= -1: return w * 0.5, "BUY"
    if dev >= 2:  return w, "SELL"
    if dev >= 1:  return w * 0.5, "SELL"
    return 0, "NEUTRAL"


def score_macd(row, w):
    if row.get("macd_turning_up", False):   return w, "BUY"
    if row.get("macd_turning_down", False): return w, "SELL"
    return 0, "NEUTRAL"


def score_trend(row, w):
    t = row.get("trend", "SIDEWAYS")
    if t == "UPTREND":   return w, "BUY"
    if t == "DOWNTREND": return w, "SELL"
    return 0, "NEUTRAL"


def score_squeeze(row, w):
    """Squeeze ateşlendiyse bonus puan."""
    if row.get("squeeze_fire", False):
        # Ateşlenme yönü: MACD histogram pozitifse yukarı, negatifse aşağı
        hist = row.get("macd_hist", 0)
        return w, ("BUY" if hist > 0 else "SELL")
    return 0, "NEUTRAL"


def calculate_score(row: pd.Series, config: dict) -> dict:
    """Tüm göstergeleri puanla → composite skor üret."""
    w = config["scoring"]["weights"]
    s = config["strategy"]

    scorers = {
        "bollinger":  score_bollinger(row, w["bollinger"]),
        "keltner":    score_keltner(row, w["keltner"]),
        "zscore":     score_zscore(row, w["zscore"]),
        "rsi":        score_rsi(row, w["rsi"], s),
        "stochastic": score_stochastic(row, w["stochastic"], s),
        "volume":     score_volume(row, w["volume_spike"]),
        "vwap":       score_vwap(row, w["vwap"]),
        "macd":       score_macd(row, w["macd"]),
        "trend":      score_trend(row, w["trend"]),
        "squeeze":    score_squeeze(row, w["squeeze"]),
    }

    buy_score = sum(sc for sc, d in scorers.values() if d == "BUY")
    sell_score = sum(sc for sc, d in scorers.values() if d == "SELL")

    if buy_score > sell_score:
        final_score, direction = buy_score, "BUY"
    elif sell_score > buy_score:
        final_score, direction = sell_score, "SELL"
    else:
        final_score, direction = 0, "NEUTRAL"

    th = config["scoring"]["thresholds"]
    if final_score >= th["strong"]:    level = "STRONG"
    elif final_score >= th["moderate"]: level = "MODERATE"
    elif final_score >= th["weak"]:     level = "WEAK"
    else:                               level = "NONE"

    label = f"{level}_{direction}" if level != "NONE" else "NO_SIGNAL"

    details = {k: {"score": round(v[0], 1), "dir": v[1]} for k, v in scorers.items()}

    return {
        "buy_score": round(buy_score, 1),
        "sell_score": round(sell_score, 1),
        "final_score": round(final_score, 1),
        "direction": direction,
        "level": level,
        "label": label,
        "details": details,
        "squeeze_on": bool(row.get("squeeze_on", False)),
        "squeeze_fire": bool(row.get("squeeze_fire", False)),
    }
