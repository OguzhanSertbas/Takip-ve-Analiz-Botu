"""
🦇 SILENT GUARDIAN v4 — Risk Engine
=====================================
Half-Kelly pozisyon boyutu + TP/SL hedefler + Risk:Ödül oranı

Muhasebeci Analojisi:
    Bu modül "bütçe kontrol" departmanıdır.
    Strateji motoru "nereye yatırım yapalım" der,
    Risk motoru "ne kadar ve hangi koruma ile" der.
"""

import math


def calculate_stop_loss(price: float, atr: float, direction: str,
                        multiplier: float = 2.0) -> dict:
    """
    ATR bazlı stop-loss hesapla.

    BUY sinyali → SL = giriş - (2 × ATR)
    SELL sinyali → SL = giriş + (2 × ATR)
    """
    distance = atr * multiplier

    if direction == "BUY":
        sl_price = price - distance
        sl_pct = (distance / price) * 100
    else:
        sl_price = price + distance
        sl_pct = (distance / price) * 100

    return {
        "sl_price": round(sl_price, 2),
        "sl_distance": round(distance, 2),
        "sl_pct": round(sl_pct, 2),
    }


def calculate_targets(price: float, atr: float, bb_mid: float,
                      vwap: float, direction: str) -> list[dict]:
    """
    Kademeli hedef fiyatlar hesapla.

    TP1: Bollinger orta bant (muhafazakar)
    TP2: VWAP seviyesi (orta)
    TP3: 3×ATR mesafesi (agresif)
    """
    targets = []

    if direction == "BUY":
        # TP1: BB orta bant
        tp1 = bb_mid
        # TP2: VWAP (eğer VWAP > BB mid ise)
        tp2 = max(vwap, bb_mid + atr)
        # TP3: 3×ATR yukarı
        tp3 = price + (3 * atr)
    else:
        tp1 = bb_mid
        tp2 = min(vwap, bb_mid - atr)
        tp3 = price - (3 * atr)

    for i, (tp, label) in enumerate([(tp1, "Muhafazakar"), (tp2, "Orta"), (tp3, "Agresif")]):
        pct = abs((tp - price) / price) * 100
        targets.append({
            "level": i + 1,
            "label": label,
            "price": round(tp, 2),
            "pct": round(pct, 2),
        })

    return targets


def calculate_half_kelly(win_rate: float = 0.55, avg_win: float = 2.0,
                         avg_loss: float = 1.0, half: bool = True) -> float:
    """
    Half-Kelly pozisyon boyutu.

    Kelly: f* = (p × b - q) / b
    p = kazanma olasılığı
    b = ortalama kazanç / ortalama kayıp
    q = 1 - p

    Half-Kelly = f* / 2 (daha güvenli)

    Mean reversion stratejileri genelde %55-65 win rate.
    Varsayılan: %55 win, 2:1 R:R
    """
    if avg_loss == 0:
        return 0.02  # Minimum %2

    b = avg_win / avg_loss
    q = 1 - win_rate

    kelly = (win_rate * b - q) / b

    if kelly <= 0:
        return 0.01  # Kelly negatifse minimum pozisyon

    if half:
        kelly = kelly / 2

    # Max %10, min %1 sınırla
    return round(max(0.01, min(0.10, kelly)), 4)


def calculate_position_size(portfolio: float, price: float, sl_distance: float,
                            max_risk_pct: float = 0.02, kelly_fraction: float = None) -> dict:
    """
    Pozisyon boyutu hesapla.

    Yöntem 1 (Sabit Risk): Max riskin = portföyün %2'si
        Hisse adedi = (Portföy × %2) / SL mesafesi

    Yöntem 2 (Kelly): Kelly fraksiyonu ile
        Hisse adedi = (Portföy × Kelly) / Fiyat
    """
    # Yöntem 1: Sabit risk
    max_dollar_risk = portfolio * max_risk_pct
    shares_by_risk = math.floor(max_dollar_risk / sl_distance) if sl_distance > 0 else 0
    cost_by_risk = shares_by_risk * price

    # Yöntem 2: Kelly (eğer varsa)
    if kelly_fraction:
        kelly_allocation = portfolio * kelly_fraction
        shares_by_kelly = math.floor(kelly_allocation / price)
        # İkisinden küçük olanı al (güvenlik)
        shares = min(shares_by_risk, shares_by_kelly)
    else:
        shares = shares_by_risk

    shares = max(1, shares)  # En az 1 hisse
    total_cost = shares * price
    portfolio_pct = (total_cost / portfolio) * 100

    return {
        "shares": shares,
        "total_cost": round(total_cost, 2),
        "portfolio_pct": round(portfolio_pct, 2),
        "max_loss": round(shares * sl_distance, 2),
        "max_loss_pct": round((shares * sl_distance / portfolio) * 100, 2),
    }


def calculate_risk_reward(price: float, sl_price: float, targets: list[dict],
                          direction: str) -> list[dict]:
    """Her hedef için Risk:Ödül oranı hesapla."""
    risk = abs(price - sl_price)
    if risk == 0:
        return targets

    for tp in targets:
        reward = abs(tp["price"] - price)
        tp["rr_ratio"] = round(reward / risk, 2) if risk > 0 else 0
        tp["risk_usd"] = round(risk, 2)
        tp["reward_usd"] = round(reward, 2)

    return targets


def generate_risk_report(price: float, row_data: dict, config: dict) -> dict:
    """
    Tam risk raporu üret.
    """
    risk_cfg = config["risk"]
    direction = row_data.get("direction", "BUY")
    atr = row_data.get("atr", price * 0.02)
    bb_mid = row_data.get("bb_mid", price)
    vwap = row_data.get("vwap", price)

    # Stop-loss
    sl = calculate_stop_loss(price, atr, direction, risk_cfg["atr_stop_multiplier"])

    # Hedefler
    targets = calculate_targets(price, atr, bb_mid, vwap, direction)

    # Risk:Ödül
    targets = calculate_risk_reward(price, sl["sl_price"], targets, direction)

    # Kelly
    kelly = calculate_half_kelly(half=risk_cfg["half_kelly"])

    # Pozisyon boyutu
    position = calculate_position_size(
        portfolio=risk_cfg["portfolio_size"],
        price=price,
        sl_distance=sl["sl_distance"],
        max_risk_pct=risk_cfg["max_risk_per_trade_pct"] / 100,
        kelly_fraction=kelly,
    )

    # Volatilite seviyesi
    atr_pct = (atr / price) * 100
    vol_level = "HIGH" if atr_pct > 3 else ("MEDIUM" if atr_pct > 1.5 else "LOW")

    return {
        "stop_loss": sl,
        "targets": targets,
        "kelly_fraction": kelly,
        "position": position,
        "volatility": vol_level,
        "atr": round(atr, 2),
        "atr_pct": round(atr_pct, 2),
    }
