import json
import os
import time
import random
from datetime import datetime
from dotenv import load_dotenv
import hashlib

# === Paths ===
IDENTIFIER_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/ebay_item_identifiers.json"
RESULT_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/rocket_results.json"
LOG_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/rocket_sauce.log"

# === Config ===
load_dotenv("/Users/stephentaykor/Desktop/flipper_Simulation/Flipper_AI/.env")

# === Logging ===
def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# === Load Identifiers ===
def load_ebay_identifiers():
    if not os.path.exists(IDENTIFIER_FILE):
        log("❌ No ebay_item_identifiers.json found — run the eBay scraper first.")
        return []
    with open(IDENTIFIER_FILE, "r") as f:
        data = json.load(f)
    log(f"📦 Loaded {len(data)} eBay identifiers.")
    return data

# === ASIN Conversion Logic (local deterministic pseudo generator) ===
def make_fake_asin(identifier):
    """Generate a consistent fake ASIN based on GTIN/EAN/UPC or item_id."""
    base = identifier.get("gtin") or identifier.get("upc") or identifier.get("ean") or identifier.get("item_id")
    if not base:
        return None
    digest = hashlib.sha1(base.encode()).hexdigest().upper()
    return "B0" + digest[:8]  # mimic Amazon ASIN style

# === Main Processor ===
def main():
    log("🚀 Rocket Sauce: Starting local ASIN mapping from eBay identifiers.")
    identifiers = load_ebay_identifiers()
    if not identifiers:
        log("❌ No identifiers to process — exiting.")
        return

    results = []
    for idx, item in enumerate(identifiers, start=1):
        asin = make_fake_asin(item)
        if asin:
            result = {
                "item_id": item.get("item_id"),
                "asin": asin,
                "brand": item.get("brand"),
                "gtin": item.get("gtin"),
                "upc": item.get("upc"),
                "ean": item.get("ean"),
                "timestamp": datetime.now().isoformat()
            }
            results.append(result)
            log(f"✅ [{idx}/{len(identifiers)}] Generated ASIN {asin} for {item.get('item_id')}")
        else:
            log(f"⚠️ [{idx}/{len(identifiers)}] No identifiers for {item.get('item_id')}")
        time.sleep(random.uniform(0.5, 1.2))  # small delay for realism

    # Save results
    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    with open(RESULT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    log(f"🏁 Completed Rocket Sauce run: {len(results)} ASINs written to {RESULT_FILE}")

if __name__ == "__main__":
    main()
