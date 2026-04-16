from client import load_config, fetch_ticker, get_watchlist
from indicators import calculate_all
from scoring import calculate_score
from risk_engine import generate_risk_report

def analyze_single(symbol: str, config: dict = None, sector: str = "N/A", market: str = "US") -> dict | None:
    if config is None: config = load_config()
    df = fetch_ticker(symbol, config)
    if df is None or len(df) < 30: return None
    try:
        df = calculate_all(df, config)
        last = df.iloc[-1]
        score_result = calculate_score(last, config)
        result = {
            "symbol": symbol, "sector": sector, "market": market,
            "price": round(last["close"], 2), "trend": last.get("trend", "N/A"),
            "rsi": round(last.get("rsi", 50), 1), "final_score": score_result["final_score"],
            "label": score_result["label"], "direction": score_result["direction"],
            "level": score_result["level"], "details": score_result["details"],
            "squeeze_on": score_result.get("squeeze_on", False),
            "squeeze_fire": score_result.get("squeeze_fire", False)
        }
        result["risk"] = generate_risk_report(result["price"], last, config)
        return result
    except: return None

def scan_all(config: dict = None):
    if config is None: config = load_config()
    watchlist = get_watchlist(config)
    signals = []
    for item in watchlist:
        res = analyze_single(item["symbol"], config, item["sector"], item["market"])
        if res and res["level"] != "NONE": signals.append(res)
    return signals
