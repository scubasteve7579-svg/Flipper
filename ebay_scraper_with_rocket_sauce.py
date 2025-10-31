#!/usr/bin/env python3
"""
ebay_scraper_with_rocket_sauce.py

What this does (in order):
0) Quick RocketSource connectivity PRECHECK (multipart upload) so you know it's alive
1) Refresh eBay OAuth token
2) Scrape eBay listings by category + condition (PRODUCT fieldgroup enabled)
3) Extract identifiers (brand/mpn/gtin/upc/ean)
4) Send to RocketSource (multipart upload) to map → ASINs
5) Save ASINs for Keepa and rocket_results.json
6) Repeat every 2 hours (same cadence as your other script)
"""

import os, json, time, random, base64, csv, io
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import subprocess

# ───────────────────────────────────────────────
# PATHS / CONFIG
# ───────────────────────────────────────────────
BASE_DIR = "/Users/stephentaykor/Desktop/flipper_Simulation"
ENV_FILE = f"{BASE_DIR}/Flipper_AI/.env"

OUTPUT_DIR         = f"{BASE_DIR}/my_items_safe"
RECENT_DIR         = f"{BASE_DIR}/my_items_recent"
ITEMS_FILE         = f"{OUTPUT_DIR}/ebay_items.json"
IDENTIFIERS_FILE   = f"{OUTPUT_DIR}/ebay_item_identifiers.json"
ROCKET_RESULTS_FILE= f"{OUTPUT_DIR}/rocket_results.json"
KEEPA_INPUT_FILE   = f"{OUTPUT_DIR}/keepa_ebay_ids.json"
PIPELINE_LOG       = f"{OUTPUT_DIR}/ebay_scraper_with_rocket_sauce.log"
PRECHECK_LOG       = f"{OUTPUT_DIR}/rocket_precheck.log"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(RECENT_DIR, exist_ok=True)

REQUEST_DELAY = (2.5, 5.0)
MAX_RETRIES   = 5
RUN_INTERVAL_SECONDS = 2 * 60 * 60   # 2 hours

# RocketSource endpoint that requires multipart form
ROCKETSOURCE_ENDPOINT = "https://app.rocketsource.io/v1/map"   # chosen for speed + your server message (expects multipart)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

CATEGORIES = [
    {"id": "293",   "name": "Electronics"},
    {"id": "58058", "name": "Computers/Tablets & Networking"},
    {"id": "172008","name": "Cell Phones & Accessories"},
    {"id": "15032", "name": "Sporting Goods"},
]
CONDITIONS = [
    {"id": "1000", "name": "New"},
    {"id": "3000", "name": "Used"}
]

# ───────────────────────────────────────────────
# LOGGING
# ───────────────────────────────────────────────
def log(path, msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(path, "a") as f:
        f.write(line + "\n")

def plog(msg): log(PIPELINE_LOG, msg)
def prelog(msg): log(PRECHECK_LOG, msg)

def log_both(msg):
    plog(msg)
    prelog(msg)

# ───────────────────────────────────────────────
# ENV / AUTH
# ───────────────────────────────────────────────
def load_env():
    load_dotenv(ENV_FILE)
    conf = {
        "EBAY_CLIENT_ID":      os.getenv("EBAY_CLIENT_ID"),
        "EBAY_CLIENT_SECRET":  os.getenv("EBAY_CLIENT_SECRET"),
        "EBAY_REFRESH_TOKEN":  os.getenv("EBAY_REFRESH_TOKEN"),
        "ROCKET_KEY":          os.getenv("rocket_sauce_API_KEY"),
        "KEEPA_KEY":           os.getenv("keepa_API"),  # not used here, but helpful later
    }
    return conf

def refresh_ebay_token(client_id, client_secret, refresh_token):
    plog("🔑 Refreshing eBay OAuth token")
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": "https://api.ebay.com/oauth/api_scope"
        },
        timeout=30,
    )
    if resp.status_code == 200:
        plog("✅ Token refreshed successfully")
        return resp.json()["access_token"]
    plog(f"❌ Failed to refresh token: {resp.status_code} {resp.text}")
    return None

# ───────────────────────────────────────────────
# EBAY SCRAPER (PRODUCT fieldgroup enabled)
# ───────────────────────────────────────────────
def append_json(path, data_list):
    existing = []
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                existing = json.load(f)
        except Exception:
            existing = []
    existing.extend(data_list)
    with open(path, "w") as f:
        json.dump(existing, f, indent=2)

def scrape_ebay_items(token):
    plog("🔍 Scraping eBay items (with PRODUCT fieldgroup)...")
    headers = {"Authorization": f"Bearer {token}", "User-Agent": random.choice(USER_AGENTS)}
    all_items, identifiers = [], []

    for cat in CATEGORIES:
        for cond in CONDITIONS:
            params = {
                "category_ids": cat["id"],
                "q": cat["name"].lower(),
                "limit": "200",
                "filter": f"conditionIds:{cond['id']}",
                "fieldgroups": "PRODUCT",  # 👈 this is key to populate product identifiers
            }
            try:
                resp = requests.get(
                    "https://api.ebay.com/buy/browse/v1/item_summary/search",
                    headers=headers, params=params, timeout=60
                )
                plog(f"📦 {cat['name']} ({cond['name']}) → {resp.status_code}")
            except Exception as e:
                plog(f"💥 eBay request error: {e}")
                time.sleep(3)
                continue

            if resp.status_code != 200:
                time.sleep(3)
                continue

            data = resp.json()
            for i in data.get("itemSummaries", []):
                iid = i.get("itemId")
                title = i.get("title", "")
                all_items.append({
                    "item_id": iid,
                    "title": title,
                    "price": i.get("price", {}).get("value"),
                    "url": i.get("itemWebUrl"),
                    "condition": i.get("condition"),
                    "category": cat["name"],
                    "scraped_at": datetime.now().isoformat(),
                })
                prod = (i.get("product") or {})  # might be missing
                if prod:
                    identifiers.append({
                        "item_id": iid,
                        "title": title,
                        "brand": prod.get("brand"),
                        "mpn":   prod.get("mpn"),
                        "gtin":  prod.get("gtin"),
                        "upc":   prod.get("upc"),
                        "ean":   prod.get("ean"),
                    })
            time.sleep(random.uniform(*REQUEST_DELAY))

    append_json(ITEMS_FILE, all_items)
    append_json(IDENTIFIERS_FILE, identifiers)
    plog(f"💾 Saved {len(all_items)} items, {len(identifiers)} identifiers.")
    return identifiers

# ───────────────────────────────────────────────
# ROCKETSOURCE MULTIPART HELPERS
# ───────────────────────────────────────────────
def _identifiers_to_json_bytes(id_list):
    # Send a compact JSON array with only useful keys for mapping
    slim = []
    for d in id_list:
        slim.append({
            "item_id": d.get("item_id"),
            "title":   d.get("title"),
            "brand":   d.get("brand"),
            "mpn":     d.get("mpn"),
            "gtin":    d.get("gtin"),
            "upc":     d.get("upc"),
            "ean":     d.get("ean"),
        })
    return json.dumps(slim, separators=(",", ":")).encode("utf-8")

def _identifiers_to_csv_bytes(id_list):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["item_id","title","brand","mpn","gtin","upc","ean"])
    writer.writeheader()
    for d in id_list:
        writer.writerow({
            "item_id": d.get("item_id",""),
            "title":   (d.get("title") or "")[:200],
            "brand":   d.get("brand",""),
            "mpn":     d.get("mpn",""),
            "gtin":    d.get("gtin",""),
            "upc":     d.get("upc",""),
            "ean":     d.get("ean",""),
        })
    return output.getvalue().encode("utf-8")

def rocketsource_precheck(rocket_key):
    """Tiny multipart call first so you see success/fail BEFORE scraping."""
    prelog("🧪 RocketSource precheck (multipart) starting...")
    headers = {"Authorization": f"Bearer {rocket_key}"}
    probe_items = [
        {"item_id":"probe-1","title":"Test Item 1","brand":"ProbeCo","mpn":"X1","gtin":"","upc":"012345678905","ean":""},
        {"item_id":"probe-2","title":"Test Item 2","brand":"ProbeCo","mpn":"X2","gtin":"00012345600012","upc":"","ean":""},
    ]

    # Try JSON multipart first
    files = {
        "file": ("items.json", _identifiers_to_json_bytes(probe_items), "application/json")
    }
    data = {"marketplace":"amazon"}

    try:
        r = requests.post(ROCKETSOURCE_ENDPOINT, headers=headers, data=data, files=files, timeout=30)
        prelog(f"🔌 JSON-multipart status: {r.status_code}")
        if 200 <= r.status_code < 300:
            prelog(f"✅ Precheck OK (JSON multipart). Snippet: {r.text[:200]}")
            return True
        else:
            prelog(f"⚠️ JSON multipart rejected: {r.text[:200]}")
    except Exception as e:
        prelog(f"💥 JSON multipart exception: {e}")

    # Fallback: CSV multipart
    files = {
        "file": ("items.csv", _identifiers_to_csv_bytes(probe_items), "text/csv")
    }
    try:
        r = requests.post(ROCKETSOURCE_ENDPOINT, headers=headers, data=data, files=files, timeout=30)
        prelog(f"🔌 CSV-multipart status: {r.status_code}")
        if 200 <= r.status_code < 300:
            prelog(f"✅ Precheck OK (CSV multipart). Snippet: {r.text[:200]}")
            return True
        else:
            prelog(f"⚠️ CSV multipart rejected: {r.text[:200]}")
    except Exception as e:
        prelog(f"💥 CSV multipart exception: {e}")

    prelog("❌ Precheck failed.")
    return False

def run_rocket_sauce(api_key, identifiers):
    log_both(f"🚀 Sending {len(identifiers)} identifiers to RocketSource (multipart upload)")
    url = "https://app.rocketsource.io/v1/map"
    headers = {"Authorization": f"Bearer {api_key}"}

    asin_map = {}
    batch_size = 200

    for i in range(0, len(identifiers), batch_size):
        batch = identifiers[i:i+batch_size]

        # Create JSON string as file content
        file_content = json.dumps(batch, separators=(",", ":"))
        files = {
            "file": ("items.json", file_content, "application/json")
        }
        data = {"marketplace": "amazon"}

        try:
            r = requests.put(url, headers=headers, data=data, files=files, timeout=90)  # <-- changed to PUT
            if 200 <= r.status_code < 300:
                results = r.json().get("results", [])
                for r_item in results:
                    if "asin" in r_item and "item_id" in r_item:
                        asin_map[r_item["item_id"]] = r_item["asin"]
                log_both(f"✅ Batch {i//batch_size+1}: {len(results)} ASINs mapped")
            else:
                log_both(f"⚠️ RocketSource error {r.status_code}: {r.text[:200]}")
        except Exception as e:
            log_both(f"💥 RocketSource exception: {e}")

        time.sleep(3)

    asin_file = f"{OUTPUT_DIR}/rocket_results.json"
    with open(asin_file, "w") as f:
        json.dump(asin_map, f, indent=2)
    log_both(f"💾 Saved {len(asin_map)} ASINs to {asin_file}")
    return asin_map

# ───────────────────────────────────────────────
# KEEPAs handoff (simple writer)
# ───────────────────────────────────────────────
def write_keepa_ids_from_asin_map(asin_map):
    asin_ids = sorted(set(asin_map.values()))
    with open(KEEPA_INPUT_FILE, "w") as f:
        json.dump(asin_ids, f, indent=2)
    plog(f"🧩 Saved {len(asin_ids)} ASINs to {KEEPA_INPUT_FILE} for Keepa.")

# ───────────────────────────────────────────────
# ONE CYCLE OF THE PIPELINE
# ───────────────────────────────────────────────
def run_once():
    print("🚀 ebay_scraper_with_rocket_sauce.py started successfully", flush=True)
    cfg = load_env()
    if not all([cfg["EBAY_CLIENT_ID"], cfg["EBAY_CLIENT_SECRET"], cfg["EBAY_REFRESH_TOKEN"], cfg["ROCKET_KEY"]]):
        plog("❌ Missing one or more required API keys in .env")
        return

    # 0) RocketSource precheck FIRST so you see if it’s alive
    pre_ok = rocketsource_precheck(cfg["ROCKET_KEY"])
    if not pre_ok:
        plog("⛔ Precheck failed — not running scrape to avoid wasted calls.")
        return

    # 1) Auth
    token = refresh_ebay_token(cfg["EBAY_CLIENT_ID"], cfg["EBAY_CLIENT_SECRET"], cfg["EBAY_REFRESH_TOKEN"])
    if not token:
        return

    # 2) Scrape + identifiers
    identifiers = scrape_ebay_items(token)
    if not identifiers:
        plog("⚠️ No identifiers found. Exiting.")
        return

    # 3) RocketSource mapping
    asin_map = run_rocket_sauce(cfg["ROCKET_KEY"], identifiers)

    # 4) Save results for Keepa + rocket_results.json
    if asin_map:
        write_keepa_ids_from_asin_map(asin_map)
        with open(ROCKET_RESULTS_FILE, "w") as f:
            json.dump(asin_map, f, indent=2)
        plog(f"💾 rocket_results.json written with {len(asin_map)} mappings.")
    else:
        plog("⚠️ No ASINs returned from RocketSource.")

# ───────────────────────────────────────────────
# CONTINUOUS LOOP
# ───────────────────────────────────────────────
def auto_loop():
    plog(f"🌀 Starting continuous eBay→RocketSource→Keepa loop (every {RUN_INTERVAL_SECONDS//3600}h)")
    cycle = 1
    while True:
        plog(f"🚀 Starting cycle #{cycle}")
        try:
            run_once()
            plog(f"✅ Cycle #{cycle} finished.")
        except Exception as e:
            plog(f"💥 Error in cycle #{cycle}: {e}")
        plog(f"⏸ Sleeping for {RUN_INTERVAL_SECONDS/60:.0f} minutes before next run...")
        time.sleep(RUN_INTERVAL_SECONDS)
        cycle += 1

# ───────────────────────────────────────────────
if __name__ == "__main__":
    # Run one cycle immediately so you get instant feedback,
    # then continue with the standard 2h cadence.
    run_once()
    plog("⏳ Entering scheduled loop...")
    auto_loop()