#!/usr/bin/env python3
import os, json, csv, io, requests
from dotenv import load_dotenv
from datetime import datetime

# ====== CONFIG ======
BASE = "/Users/stephentaykor/Desktop/flipper_Simulation"
ENV_FILE = f"{BASE}/Flipper_AI/.env"
OUTPUT_DIR = f"{BASE}/my_items_safe"
IDENTIFIERS = f"{OUTPUT_DIR}/ebay_item_identifiers.json"
RESULT_FILE = f"{OUTPUT_DIR}/rocket_upload_test_result.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

ENDPOINTS = [
    "https://app.rocketsource.io/api/v3/scans",
    "https://app.rocketsource.io/api/v1/scans",
    "https://api.rocketsauce.ai/v1/map",
    "https://api.rocketsource.ai/v3/scans",
]

# ====== LOAD ENV ======
load_dotenv(ENV_FILE)
API_KEY = os.getenv("rocket_sauce_API_KEY")

def log(msg):
    print(msg, flush=True)

def load_ids():
    if not os.path.exists(IDENTIFIERS):
        return []
    with open(IDENTIFIERS) as f:
        return json.load(f)[:441]  # small batch

def to_json_bytes(items):
    return json.dumps(items, separators=(",",":")).encode()

def to_csv_bytes(items):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["item_id","title","brand","mpn","gtin","upc","ean"])
    for x in items:
        w.writerow([
            x.get("item_id",""),
            x.get("title","")[:200],
            x.get("brand",""),
            x.get("mpn",""),
            x.get("gtin",""),
            x.get("upc",""),
            x.get("ean",""),
        ])
    return buf.getvalue().encode()

def dns_ok(url):
    try:
        requests.get(url.split("/")[0] + "//" + url.split("/")[2], timeout=2)
        return True
    except:
        return False

def attempt(url, items):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    results = []

    modes = [
        ("json","file", to_json_bytes(items), "application/json"),
        ("json","items", to_json_bytes(items), "application/json"),
        ("json","upload", to_json_bytes(items), "application/json"),
        ("csv","file", to_csv_bytes(items), "text/csv"),
        ("csv","items", to_csv_bytes(items), "text/csv"),
        ("csv","upload", to_csv_bytes(items), "text/csv"),
        ("csv","csv", to_csv_bytes(items), "text/csv"),
        ("body-json", None, json.dumps(items), "application/json"),
    ]

    for mode, field, content, ctype in modes:
        try:
            if field is None:
                r = requests.post(url, headers=headers, json=items, timeout=20)
            else:
                files = { field: ("items."+("json" if mode=="json" else "csv"), content, ctype) }
                data = {"marketplace":"amazon"}
                r = requests.post(url, headers=headers, data=data, files=files, timeout=20)

            status = r.status_code
            text = r.text[:200]

            log(f"→ POST {url} ({mode}, field={field}) → {status}")

            results.append((mode, field, status, text))
        except Exception as e:
            log(f"❌ EXC for {url} ({mode},{field}): {e}")
            results.append((mode, field, None, str(e)))

    return results


if __name__ == "__main__":
    if not API_KEY:
        print("❌ rocket_sauce_API_KEY missing in .env")
        exit(1)

    ids = load_ids()
    if not ids:
        print("⚠️ No ebay_item_identifiers.json found or empty!")
        ids = [
            {"item_id":"test1","title":"Test Item","brand":"Test","upc":"012345678905"},
            {"item_id":"test2","title":"Test Item 2","ean":"00012345600012"}
        ]

    log(f"✅ Loaded {len(ids)} identifiers from file")
    summary = {}

    for url in ENDPOINTS:
        ok = dns_ok(url)
        log(f"\n---\nTrying endpoint: {url} (DNS OK? {ok})")
        res = attempt(url, ids)
        summary[url] = res

    with open(RESULT_FILE,"w") as f:
        json.dump(summary,f,indent=2)

    log(f"\n✅ Finished multipart test.")
    log(f"📁 Results saved to: {RESULT_FILE}")
