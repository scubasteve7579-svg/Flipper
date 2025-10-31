#!/usr/bin/env python3
"""
keepa_query.py
Continuously fetches sales and price data from Keepa for items listed in
my_items_safe/keepa_ebay_ids.json. Runs every 30 minutes.
"""

import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from keepa import Keepa

# ───────────────────────────────────────────────
# CONFIGURATION
# ───────────────────────────────────────────────
BASE_DIR = "/Users/stephentaykor/Desktop/flipper_Simulation"
ENV_FILE = f"{BASE_DIR}/Flipper_AI/.env"
INPUT_FILE = f"{BASE_DIR}/my_items_safe/keepa_ebay_ids.json"
OUTPUT_FILE = f"{BASE_DIR}/my_items_safe/keepa_sold_data.json"
LOG_FILE = f"{BASE_DIR}/my_items_safe/keepa_query.log"

MAX_BATCH_SIZE = 100           # Process 100 IDs per loop
LOOP_INTERVAL = 1800           # 30 minutes in seconds
SLEEP_BETWEEN_CALLS = 2        # seconds between Keepa requests

# ───────────────────────────────────────────────
# HELPERS
# ───────────────────────────────────────────────
def log(msg: str):
    line = f"{datetime.now().isoformat()} | {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def load_ids() -> list:
    """Load up to MAX_BATCH_SIZE IDs from keepa_ebay_ids.json"""
    if not os.path.exists(INPUT_FILE):
        log(f"⚠️ Input file not found: {INPUT_FILE}")
        return []
    try:
        with open(INPUT_FILE, "r") as f:
            data = json.load(f)
            if not isinstance(data, list):
                log("⚠️ Invalid JSON format in keepa_ebay_ids.json")
                return []
            return data[:MAX_BATCH_SIZE]
    except Exception as e:
        log(f"❌ Error reading input file: {e}")
        return []

def save_results(results: list):
    """Append new results to keepa_sold_data.json (deduplicated)"""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r") as f:
                existing = json.load(f)
        except Exception:
            existing = []
    else:
        existing = []
    combined = {i["item_id"]: i for i in existing + results}.values()
    with open(OUTPUT_FILE, "w") as f:
        json.dump(list(combined), f, indent=2)
    log(f"💾 Saved {len(results)} new items. Total in file: {len(combined)}")

# ───────────────────────────────────────────────
# MAIN SCRAPER
# ───────────────────────────────────────────────
def run_keepa_query(api: Keepa):
    ids = load_ids()
    if not ids:
        log("⚠️ No IDs found in keepa_ebay_ids.json — skipping this run.")
        return

    log(f"📦 Loaded {len(ids)} IDs for this run.")
    flipper_items = []

    for i, asin in enumerate(ids, start=1):
        log(f"🔍 [{i}/{len(ids)}] Querying Keepa for {asin}")
        try:
            products = api.query(asin, domain=1, stats="sold,price")

            for product in products:
                if not hasattr(product, "asin"):
                    continue

                title = getattr(product, "title", "Unknown Title")
                csv_data = getattr(product, "csv", None)

                if csv_data and len(csv_data) > 1:
                    first_timestamp = csv_data[0][0]
                    last_timestamp = csv_data[-1][0]
                    first_sale = datetime.fromtimestamp(first_timestamp).strftime('%Y-%m-%d')
                    last_sale = datetime.fromtimestamp(last_timestamp).strftime('%Y-%m-%d')
                    duration_days = (datetime.fromtimestamp(last_timestamp) - datetime.fromtimestamp(first_timestamp)).days
                    price = str(csv_data[-1][1]) if csv_data[-1][1] else "N/A"

                    flipper_items.append({
                        "item_id": product.asin,
                        "title": title,
                        "listing_date": first_sale,
                        "duration": f"{duration_days} days" if duration_days > 0 else "1 day",
                        "sold_price": price,
                        "url": f"https://www.amazon.com/dp/{product.asin}",
                        "categoryPath": getattr(product, 'category', 'Unknown')
                    })
                    log(f"✅ Processed {asin} — {title[:40]}... Sold for {price}")
                else:
                    log(f"⚠️ No sales data for {asin}")

            time.sleep(SLEEP_BETWEEN_CALLS)

        except Exception as e:
            log(f"💥 Error on {asin}: {e}")
            time.sleep(5)

    if flipper_items:
        save_results(flipper_items)
    else:
        log("ℹ️ No new data this run.")

# ───────────────────────────────────────────────
# LOOP
# ───────────────────────────────────────────────
def main():
    load_dotenv(ENV_FILE)
    api_key = os.getenv("keepa_API")
    if not api_key:
        raise ValueError("❌ No Keepa API key found in .env (keepa_API=...)")

    api = Keepa(api_key)
    log(f"🔑 Keepa API initialized ({api_key[:10]}...)")

    while True:
        log("🚀 Starting new Keepa query cycle")
        try:
            run_keepa_query(api)
        except Exception as e:
            log(f"💥 Fatal error in main loop: {e}")
        log(f"⏸ Sleeping {LOOP_INTERVAL/60:.1f} minutes before next run")
        time.sleep(LOOP_INTERVAL)

# ───────────────────────────────────────────────
if __name__ == "__main__":
    main()
