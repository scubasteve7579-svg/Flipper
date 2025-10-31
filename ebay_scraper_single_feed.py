#!/usr/bin/env python3
import os, json, time, random, base64
import requests
from datetime import datetime
from dotenv import load_dotenv

# Paths
BASE = "/Users/stephentaykor/Desktop/flipper_Simulation"
ENV = f"{BASE}/Flipper_AI/.env"
OUT = f"{BASE}/my_items_safe"
ITEMS_FILE = f"{OUT}/items.json"
IDENT_FILE = f"{OUT}/identifiers.json"
KEEPA_FILE = f"{OUT}/keepa_ids.json"
LOG = f"{OUT}/ebay_scrape.log"

os.makedirs(OUT, exist_ok=True)
load_dotenv(ENV)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) Chrome/120 Safari/537.36",
]

CATS = ["293","1249","15032","281","11700","111422","15052","6000","10542"]  # Highest turnover
CONDS = ["1000","3000"]

def log(msg):
    with open(LOG, "a") as f: f.write(f"[{datetime.now()}] {msg}\n")
    print(msg)

def refresh_token():
    cid = os.getenv("EBAY_CLIENT_ID")
    sec = os.getenv("EBAY_CLIENT_SECRET")
    ref = os.getenv("EBAY_REFRESH_TOKEN")
    h = base64.b64encode(f"{cid}:{sec}".encode()).decode()

    r = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={"Authorization": f"Basic {h}", "Content-Type":"application/x-www-form-urlencoded"},
        data={"grant_type":"refresh_token","refresh_token":ref,"scope":"https://api.ebay.com/oauth/api_scope"},
        timeout=30
    )
    return r.json().get("access_token")

def append(path, data):
    old = []
    if os.path.exists(path):
        try: old = json.load(open(path))
        except: pass
    json.dump(old + data, open(path, "w"), indent=2)

def scrape():
    token = refresh_token()
    if not token: return log("TOKEN FAIL")

    log("🔍 Scraping eBay...")
    headers = {"Authorization":f"Bearer {token}","User-Agent":random.choice(USER_AGENTS)}
    all_items, all_ids = [], set()

    for cat in CATS:
        for cond in CONDS:
            offset = 0
            while True:
                p = {"category_ids":cat,"limit":"200","offset":str(offset),"filter":f"conditionIds:{cond}"}
                r = requests.get("https://api.ebay.com/buy/browse/v1/item_summary/search",headers=headers,params=p,timeout=60)
                data = r.json().get("itemSummaries",[])
                if not data: break

                for x in data:
                    all_items.append({
                        "item_id":x.get("itemId"),
                        "title":x.get("title"),
                        "price":x.get("price",{}).get("value"),
                        "url":x.get("itemWebUrl"),
                        "condition":x.get("condition"),
                        "category":cat,
                        "scraped_at":datetime.now().isoformat(),
                    })
                    for key in ("gtin","upc","ean"):
                        v = (x.get("product") or {}).get(key)
                        if v: all_ids.add(v)

                offset += 200
                time.sleep(random.uniform(1.2, 2.0))

    append(ITEMS_FILE, all_items)
    append(IDENT_FILE, [{"code":c} for c in all_ids])
    json.dump(sorted(all_ids), open(KEEPA_FILE,"w"), indent=2)

    log(f"✅ Scraped {len(all_items)} new items")
    log(f"✅ {len(all_ids)} product codes saved for Keepa")

if __name__ == "__main__":
    scrape()
