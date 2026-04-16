import time
import threading
import schedule
import logging
from client import load_config, get_watchlist
from scanner import scan_all
from report_generator import generate_scan_alert
from telegram_bot import send_message, run_bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

def scheduled_scan():
    config = load_config()
    signals = scan_all(config)
    if signals:
        send_message(generate_scan_alert(signals), config)

if __name__ == "__main__":
    config = load_config()
    # Sizin config dosyanızdaki doğru anahtar:
    interval = config["scheduler"]["scan_interval_minutes"]
    
    print(f"🦇 SILENT GUARDIAN v4 aktif. | {interval} dk tarama.")
    send_message(f"🦇 <b>SILENT GUARDIAN v4</b> aktif.\n📡 Tarama aralığı: {interval} dk", config)
    
    threading.Thread(target=run_bot, daemon=True).start()
    
    if config["scheduler"]["scan_on_start"]:
        scheduled_scan()

    schedule.every(interval).minutes.do(scheduled_scan)
    while True:
        schedule.run_pending()
        time.sleep(1)
