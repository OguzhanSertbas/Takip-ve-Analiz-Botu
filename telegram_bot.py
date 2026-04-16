import logging
import requests as req
from client import load_config
from report_generator import generate_analysis_report, generate_scan_alert

CONFIG = load_config()

def send_message(text: str, config: dict = None) -> bool:
    cfg = (config or CONFIG)["telegram"]
    url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
    try:
        res = req.post(url, json={"chat_id": cfg["chat_id"], "text": text, "parse_mode": "HTML"})
        return res.status_code == 200
    except: return False

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{CONFIG['telegram']['bot_token']}/getUpdates"
    try:
        res = req.get(url, params={"offset": offset, "timeout": 30})
        return res.json().get("result", [])
    except: return []

def run_bot():
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            text = msg.get("text", "").upper()
            if text:
                from scanner import analyze_single
                res = analyze_single(text, CONFIG)
                if res: send_message(generate_analysis_report(res))
                else: send_message(f"🔍 {text} için veri bulunamadı.")
