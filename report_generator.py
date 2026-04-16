"""
🦇 SILENT GUARDIAN v4 — Report Generator
==========================================
Çift dilli raporlar: Türkçe detay + İngilizce özet
"""

from datetime import datetime


ICONS = {
    "STRONG_BUY": "🟢", "MODERATE_BUY": "🔵", "WEAK_BUY": "🟡",
    "STRONG_SELL": "🔴", "MODERATE_SELL": "🟠", "WEAK_SELL": "🟡",
    "NO_SIGNAL": "⚪",
}

RISK_ICONS = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}


def generate_analysis_report(result: dict) -> str:
    """
    Manuel analiz raporu — kullanıcı ticker gönderdiğinde döner.
    Türkçe detay + İngilizce özet.
    """
    s = result  # kısaltma
    icon = ICONS.get(s["label"], "⚪")
    risk_icon = RISK_ICONS.get(s["risk"]["volatility"], "⚪")
    direction_tr = "AL" if s["direction"] == "BUY" else "SAT"

    # Nedenler listesi
    reasons_buy = []
    reasons_sell = []
    warnings = []

    for ind_name, ind_data in s["details"].items():
        if ind_data["score"] > 0:
            reason = _indicator_reason_tr(ind_name, ind_data, s)
            if ind_data["dir"] == "BUY":
                reasons_buy.append(f"  ✅ {reason}")
            elif ind_data["dir"] == "SELL":
                reasons_sell.append(f"  ✅ {reason}")

    # Uyarılar
    if s["squeeze_on"]:
        warnings.append("  ⚡ Squeeze AKTİF — patlama yakın!")
    if s["squeeze_fire"]:
        warnings.append("  💥 Squeeze ATEŞLENDİ — momentum başladı!")
    if s.get("trend") and s["direction"] == "BUY" and s["trend"] == "DOWNTREND":
        warnings.append("  ⚠️ Trende karşı işlem — ekstra dikkat!")
    if s.get("trend") and s["direction"] == "SELL" and s["trend"] == "UPTREND":
        warnings.append("  ⚠️ Yükseliş trendinde satım sinyali — dikkat!")

    # === TÜRKÇE RAPOR ===
    report = f"""🦇 <b>SILENT GUARDIAN — ANALİZ RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{icon} <b>{s['symbol']}</b> ({s.get('name', '')})
📊 Sektör: {s.get('sector', 'N/A')} | Piyasa: {s.get('market', 'US')}

{'─' * 28}
📊 <b>KARAR: {icon} {direction_tr}</b> (Skor: {s['final_score']}/100)
💰 Fiyat: ${s['price']}
{'─' * 28}
"""

    # Nedenler
    if s["direction"] == "BUY" and reasons_buy:
        report += "\n📈 <b>NEDEN AL?</b>\n"
        report += "\n".join(reasons_buy[:5]) + "\n"
    elif s["direction"] == "SELL" and reasons_sell:
        report += "\n📉 <b>NEDEN SAT?</b>\n"
        report += "\n".join(reasons_sell[:5]) + "\n"

    if warnings:
        report += "\n" + "\n".join(warnings) + "\n"

    # Hedefler
    if s.get("risk") and s["risk"].get("targets"):
        report += f"\n🎯 <b>HEDEFLER:</b>\n"
        for tp in s["risk"]["targets"]:
            report += f"  TP{tp['level']}: ${tp['price']} ({'+' if s['direction']=='BUY' else '-'}{tp['pct']}%) — {tp['label']}"
            if tp.get("rr_ratio"):
                report += f" | R:R {tp['rr_ratio']}"
            report += "\n"

    # Risk
    if s.get("risk"):
        r = s["risk"]
        report += f"""
🛑 <b>RİSK YÖNETİMİ:</b>
  Stop-Loss: ${r['stop_loss']['sl_price']} (-{r['stop_loss']['sl_pct']}%)
  {risk_icon} Volatilite: {r['volatility']} (ATR: %{r['atr_pct']})
"""
        if r.get("position"):
            p = r["position"]
            report += f"""  📦 Pozisyon: {p['shares']} hisse (${p['total_cost']})
  💼 Portföy: %{p['portfolio_pct']} | Max Kayıp: ${p['max_loss']}
  📐 Kelly: %{round(s['risk']['kelly_fraction'] * 100, 1)}
"""

    # Satış tetikleyicileri
    report += f"""
⚠️ <b>SATIŞ TETİKLEYİCİLERİ:</b>
  🔴 RSI > 65'e çıkarsa → kârı al
  🔴 Stop-loss'a ulaşırsa → çık
  🔴 Hacim düşerken fiyat yükselirse → zayıf hareket
  🔴 {_exit_trigger(s)}
"""

    # === İNGİLİZCE ÖZET ===
    report += f"""
{'─' * 28}
🇬🇧 <b>ENGLISH SUMMARY:</b>
{icon} {s['symbol']} — {s['label']} (Score: {s['final_score']}/100)
Price: ${s['price']} | SL: ${r['stop_loss']['sl_price'] if s.get('risk') else 'N/A'}
Risk: {r['volatility'] if s.get('risk') else 'N/A'} | Trend: {s.get('trend', 'N/A')}
{'─' * 28}
⚠️ Yatırım tavsiyesi değildir / Not investment advice.
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}"""

    return report


def generate_scan_alert(signals: list[dict]) -> str:
    """Otomatik tarama sonucu alert formatı."""
    now = datetime.now().strftime("%H:%M")

    msg = f"🦇 <b>SILENT GUARDIAN v4</b> — {now}\n"
    msg += f"{'─' * 28}\n\n"

    if not signals:
        return msg + "⚪ Sinyal yok. Alfred beklemede."

    for s in signals[:5]:  # Max 5 sinyal göster
        icon = ICONS.get(s["label"], "⚪")
        risk_icon = RISK_ICONS.get(s.get("risk", {}).get("volatility", "MEDIUM"), "⚪")

        msg += f"{icon} <b>{s['symbol']}</b> — {s['label']}\n"
        msg += f"   💰 ${s['price']} | 📊 Skor: {s['final_score']}/100\n"
        msg += f"   📈 RSI: {s.get('rsi', 'N/A')} | Z: {s.get('zscore', 0):+.2f}\n"

        if s.get("risk"):
            r = s["risk"]
            msg += f"   🛑 SL: ${r['stop_loss']['sl_price']} | {risk_icon} {r['volatility']}\n"
            if s.get("squeeze_on"): msg += f"   ⚡ Squeeze aktif!\n"

        msg += "\n"

    msg += f"{'─' * 28}\n"
    msg += f"📋 {len(signals)} sinyal | ⚠️ Paper trading\n"
    msg += f"Detay için ticker yaz → örn: <code>NVDA</code>"

    return msg


def _indicator_reason_tr(name: str, data: dict, result: dict) -> str:
    """Gösterge bazında Türkçe açıklama üret."""
    reasons = {
        "bollinger": f"Bollinger bandının {'altında' if data['dir']=='BUY' else 'üstünde'} (BB pos: {result.get('bb_position', 'N/A')})",
        "keltner": f"Keltner kanalının {'altında' if data['dir']=='BUY' else 'üstünde'}",
        "zscore": f"Z-Score: {result.get('zscore', 0):+.2f} (istatistiksel sapma)",
        "rsi": f"RSI: {result.get('rsi', 50):.1f} ({'aşırı satım' if data['dir']=='BUY' else 'aşırı alım'})",
        "stochastic": f"Stochastic: {result.get('stoch_k', 50):.1f} ({'dipte' if data['dir']=='BUY' else 'tepede'})",
        "volume": f"Hacim: {result.get('vol_ratio', 1):.1f}x ortalama {'🔥' if result.get('volume_spike') else ''}",
        "vwap": f"VWAP sapması: {result.get('vwap_dev', 0):+.2f}% (kurumsal {'alım' if data['dir']=='BUY' else 'satım'} bölgesi)",
        "macd": f"MACD momentum {'yukarı' if data['dir']=='BUY' else 'aşağı'} dönüyor",
        "trend": f"Trend: {result.get('trend', 'N/A')} (EMA desteği)",
        "squeeze": f"BB-Keltner squeeze {'ateşlendi!' if result.get('squeeze_fire') else 'aktif'}",
    }
    return reasons.get(name, f"{name}: {data['score']}p {data['dir']}")


def _exit_trigger(result: dict) -> str:
    """Dinamik çıkış tetikleyicisi."""
    if result.get("squeeze_fire"):
        return "Squeeze momentum 3 bar içinde zayıflarsa → çık"
    if result["direction"] == "BUY":
        return "BB orta banta ulaşırsa → TP1'de kısmi kâr al"
    return "BB orta banta düşerse → TP1'de kısmi kâr al"
