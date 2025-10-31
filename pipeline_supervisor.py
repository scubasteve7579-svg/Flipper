#!/usr/bin/env python3
import os, time, subprocess
from datetime import datetime, timedelta

BASE = "/Users/stephentaykor/Desktop/flipper_Simulation"
SCRAPE = f"{BASE}/Flipper_AI/ebay_scraper_single_feed.py"
VERIFY = f"{BASE}/Flipper_AI/verify_url_fast.py"
RESET_EVERY = timedelta(hours=26)

last_reset = datetime.now()

def run(cmd):
    print(f"\n▶️ Running: {cmd}\n")
    subprocess.run(["python3", cmd])

while True:
    # Daily reset every 26 hours
    if datetime.now() - last_reset > RESET_EVERY:
        print("♻️ Performing fresh restart (26h reset)")
        last_reset = datetime.now()
        # Remove Playwright cache only (NOT data)
        subprocess.run(["rm","-rf", os.path.expanduser("~/.cache/ms-playwright")])

    # Scrape → Verify
    run(SCRAPE)
    run(VERIFY)

    print("⏳ Sleeping 1 hour...")
    time.sleep(3600)
