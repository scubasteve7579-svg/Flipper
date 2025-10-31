#!/usr/bin/env python3
"""
Unified eBay Scraper + Verifier

✅ Scrapes all eBay categories
✅ Appends items to ONE items.json
✅ Saves identifiers (GTIN/UPC/EAN/MPN)
✅ Creates Keepa UPC/EAN list
✅ Verifies listings (sold/ended vs active)
✅ Moves sold → sold_items.json
✅ Keeps active → items.json
✅ Refreshes token every run
✅ Soft OAuth reset every 26h
"""

import os, json, time, random, base64, asyncio, requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# ------------------- PATHS -------------------
BASE = "/Users/stephentaykor/Desktop/flipper_Simulation"
ENV_FILE = f"{BASE}/Flipper_AI/.env"

SAFE_DIR         = f"{BASE}/my_items_safe"
ITEMS_FILE       = f"{SAFE_DIR}/items.json"
SOLD_FILE        = f"{SAFE_DIR}/sold_items.json"
IDENTIFIERS_FILE = f"{SAFE_DIR}/ebay_item_identifiers.json"
KEEPA_FILE       = f"{SAFE_DIR}/keepa_ebay_ids.json"
LOG_FILE         = f"{SAFE_DIR}/ebay_scraper.log"
LAST_SCRAPE_FILE = f"{SAFE_DIR}/last_scrape_time.json"

os.makedirs(SAFE_DIR, exist_ok=True)

# ------------------- SETTINGS -------------------
REQUEST_DELAY = (2.5, 6.0)
SOFT_RESET_HOURS = 26
VERIFY_BATCH_PRINT = 50

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
]

# ------------------- CATEGORIES -------------------
# Expanded to 50 high-market-value flipper categories
CATEGORIES = [
    # Original categories (kept as-is for consistency)
    {"id": "9355", "name": "Cell Phones & Smartphones"},
    {"id": "111422", "name": "Men's Shoes"},
    {"id": "63889", "name": "Men's Clothing"},
    {"id": "11450", "name": "Clothing, Shoes & Accessories"},
    {"id": "260010", "name": "Video Games & Consoles"},
    {"id": "58058", "name": "Computers/Tablets & Networking"},
    {"id": "293", "name": "Consumer Electronics"},
    {"id": "281", "name": "Jewelry & Watches"},
    {"id": "11233", "name": "Music"},
    {"id": "3252", "name": "Home & Garden"},
    
    # Previous new broader high-profit flipper categories
    {"id": "1", "name": "Collectibles"},  # Covers trading cards, coins, stamps, etc.
    {"id": "20081", "name": "Antiques"},  # Vintage and antique items
    {"id": "220", "name": "Toys & Hobbies"},  # Toys, models, hobbies
    {"id": "64482", "name": "Sports Memorabilia"},  # Sports cards, fan shop items
    {"id": "15032", "name": "Cell Phone Accessories"},  # Cases, chargers, etc.
    {"id": "176985", "name": "Smart Home & Surveillance"},  # Smart devices, cameras
    {"id": "15081", "name": "Drones & Accessories"},  # Drones and related gear
    {"id": "183068", "name": "Video Game Accessories"},  # Controllers, consoles, retro gaming
    {"id": "171833", "name": "Audio Equipment"},  # Headphones, speakers, microphones
    {"id": "15085", "name": "Chargers & Cables"},  # Power banks, adapters
    {"id": "171957", "name": "Laptops & Computers"},  # Laptops, PCs, workstations
    {"id": "171485", "name": "Tablets & E-Readers"},  # Tablets, Kindles, etc.
    {"id": "15099", "name": "Wearable Tech"},  # Smartwatches, fitness trackers
    {"id": "15095", "name": "Home Entertainment"},  # Projectors, TVs, streaming devices
    {"id": "176970", "name": "Home Security"},  # Cameras, alarms, sensors
    {"id": "15071", "name": "Home Audio"},  # Speakers, soundbars, receivers
    {"id": "183454", "name": "Trading Card Games"},  # Pokémon, Magic, etc.
    {"id": "11116", "name": "Coins & Paper Money"},  # Collectible currency
    {"id": "260", "name": "Stamps"},  # Philately collectibles
    {"id": "159912", "name": "Apple Products"},  # iPhones, iPads, Mac accessories
    
    # New additional high-market-value flipper categories
    {"id": "281", "name": "Luxury Watches"},  # High-end timepieces (subset of Jewelry & Watches)
    {"id": "169291", "name": "Designer Handbags"},  # Luxury bags and purses
    {"id": "267", "name": "Books & Magazines"},  # Rare books, first editions
    {"id": "11233", "name": "Vinyl Records"},  # Vintage music records
    {"id": "625", "name": "Cameras & Photo"},  # DSLR, vintage cameras
    {"id": "3858", "name": "Musical Instruments"},  # Guitars, pianos, etc.
    {"id": "111422", "name": "Sneakers"},  # Collectible footwear
    {"id": "63", "name": "Comic Books"},  # Rare comics and graphic novels
    {"id": "220", "name": "Action Figures"},  # Collectible toys
    {"id": "281", "name": "Diamonds & Gemstones"},  # Precious jewelry
    {"id": "550", "name": "Art & Paintings"},  # Fine art pieces
    {"id": "2984", "name": "Wine & Spirits"},  # Collectible beverages
    {"id": "159043", "name": "Sports Equipment"},  # Gear for sports
    {"id": "3197", "name": "Furniture"},  # Antique or designer furniture
    {"id": "631", "name": "Tools & Machinery"},  # Power tools, vintage machines
    {"id": "177831", "name": "Bicycles"},  # High-end or vintage bikes
    {"id": "16034", "name": "Camping & Hiking"},  # Outdoor gear
    {"id": "15273", "name": "Fitness Equipment"},  # Gym machines, weights
    {"id": "15052", "name": "Headphones & Earbuds"},  # Premium audio
    {"id": "15004", "name": "Smartphones Accessories"},  # Screen protectors, mounts
]

CONDITIONS = [{"id": "1000","name": "New"}, {"id": "3000","name": "Used"}]

# ------------------- HELPERS -------------------
def log(msg):
    line = f"[{datetime.now()}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f: f.write(line + "\n")

def load_env():
    load_dotenv(ENV_FILE)
    return {
        "EBAY_CLIENT_ID": os.getenv("EBAY_CLIENT_ID"),
        "EBAY_CLIENT_SECRET": os.getenv("EBAY_CLIENT_SECRET"),
        "EBAY_REFRESH_TOKEN": os.getenv("EBAY_REFRESH_TOKEN"),
    }

def append_json(path, data):
    try: x = json.load(open(path))
    except: x = []
    x.extend(data)
    json.dump(x, open(path, "w"), indent=2)

def refresh_token(cfg):
    creds = base64.b64encode(f"{cfg['EBAY_CLIENT_ID']}:{cfg['EBAY_CLIENT_SECRET']}".encode()).decode()
    r = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "refresh_token", "refresh_token": cfg["EBAY_REFRESH_TOKEN"], "scope":"https://api.ebay.com/oauth/api_scope"}
    )
    return r.json().get("access_token")

def get_last_scrape_time():
    try:
        with open(LAST_SCRAPE_FILE, "r") as f:
            data = json.load(f)
            return data.get("last_scrape")
    except:
        return None

def save_last_scrape_time(timestamp):
    with open(LAST_SCRAPE_FILE, "w") as f:
        json.dump({"last_scrape": timestamp}, f)

# ------------------- SCRAPE -------------------
def scrape(token):
    ids = []  # Collect all ids for keepa at end
    h = {"Authorization": f"Bearer {token}", "User-Agent": random.choice(USER_AGENTS)}

    last_scrape = get_last_scrape_time()
    if last_scrape:
        filter_time = f"itemStartDate:[{last_scrape}..NOW]"
    else:
        filter_time = "itemStartDate:[NOW/HOUR-2..NOW]"  # Fallback for first run

    for cat in CATEGORIES:
        items = []  # Reset items per category
        call_count = 0  # Track API calls per category (max 10)
        for cond in CONDITIONS:
            offset = 0
            while call_count < 10:  # Limit to 10 calls per category
                params = {
                    "category_ids": cat["id"], "q": cat["name"].lower(),
                    "limit": "200", "offset": offset,
                    "filter": f"conditionIds:{cond['id']},{filter_time}",
                    "fieldgroups":"PRODUCT",
                }

                r = requests.get("https://api.ebay.com/buy/browse/v1/item_summary/search", headers=h, params=params)
                batch = r.json().get("itemSummaries", [])
                call_count += 1  # Increment call count
                if not batch: break

                for it in batch:
                    items.append({
                        "item_id": it["itemId"], "title": it.get("title"),
                        "url": it.get("itemWebUrl"), "price": it.get("price",{}).get("value"),
                        "condition": it.get("condition"), "category": cat["name"],
                        "scraped_at": datetime.now().isoformat()
                    })
                    prod = it.get("product") or {}
                    ids.append({
                        "item_id": it["itemId"], "brand": prod.get("brand"),
                        "mpn": prod.get("mpn"), "gtin": prod.get("gtin"),
                        "upc": prod.get("upc"), "ean": prod.get("ean")
                    })

                if len(batch) < 200: break
                offset += 200
                time.sleep(random.uniform(*REQUEST_DELAY))
                if call_count >= 10:
                    break  # Exit condition loop if limit hit
            if call_count >= 10:
                break  # Exit category if limit hit

        # Save items at the end of each category
        append_json(ITEMS_FILE, items)
        log(f"✅ Scraped and saved {len(items)} items from category {cat['name']}")

    return ids

# ------------------- VERIFY URLs -------------------
async def verify_urls():
    try: items = json.load(open(ITEMS_FILE))
    except: return

    sold, active = [], []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        for idx, it in enumerate(items):
            if idx % VERIFY_BATCH_PRINT == 0:
                log(f"Verifying {idx}/{len(items)}")

            page = await browser.new_page()
            try:
                await page.goto(it["url"], timeout=15000)
                ended = await page.locator("text=listing has ended").count()
                removed = await page.locator("text=listing was ended").count()
                gone = await page.locator("text=longer available").count()

                (sold if (ended or removed or gone) else active).append(it)
            except:
                active.append(it)
            await page.close()
        await browser.close()

    append_json(SOLD_FILE, sold)
    json.dump(active, open(ITEMS_FILE,"w"), indent=2)
    log(f"✅ Sold moved: {len(sold)} | Active saved: {len(active)}")

# ------------------- MAIN LOOP -------------------
async def main():
    start = datetime.now()

    while True:
        if datetime.now() - start > timedelta(hours=SOFT_RESET_HOURS):
            log("♻️ Soft OAuth reset")
            load_dotenv(ENV_FILE)
            start = datetime.now()

        cfg = load_env()
        token = refresh_token(cfg)
        if not token:
            log("❌ Token failed – sleep 5m")
            time.sleep(300)
            continue

        log("🚀 Scraping...")
        ids = scrape(token)
        append_json(IDENTIFIERS_FILE, ids)

        keepa = sorted({d[k] for d in ids for k in ("gtin","upc","ean") if d.get(k)})
        json.dump(keepa, open(KEEPA_FILE,"w"), indent=2)

        # Save the current time as last scrape time
        save_last_scrape_time(datetime.now().isoformat())

        log(f"✅ Scraping complete")
        log("🔎 Verifying...")
        await verify_urls()

        log("⏳ Sleeping 2 hours...")  # Changed to 2 hours
        time.sleep(7200)  # Changed to 7200 seconds

if __name__ == "__main__":
    asyncio.run(main())
