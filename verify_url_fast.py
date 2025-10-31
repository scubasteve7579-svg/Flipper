#!/usr/bin/env python3
"""
verify_url_fast.py — AGGRESSIVE MODE
✅ Anything not verified ACTIVE = SOLD
✅ No UNKNOWN bucket
✅ No retries
"""

import asyncio, json, os, random, re, ssl
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from dotenv import load_dotenv

# ─── PATHS ───────────────────────────────────────────────
BASE = "/Users/stephentaykor/Desktop/flipper_Simulation"
ITEMS = f"{BASE}/my_items_safe/items.json"
SOLD = f"{BASE}/my_items_safe/sold_items.json"
URLS = f"{BASE}/my_items_safe/urls.json"
LOG  = f"{BASE}/my_items_safe/verifier.log"
os.makedirs(f"{BASE}/my_items_safe", exist_ok=True)

load_dotenv(f"{BASE}/Flipper_AI/.env")

# ─── CONFIG ──────────────────────────────────────────────
USE_PROXIES = True
MAX_CONCURRENCY = 20
NAV_TIMEOUT = 20000
BATCH = 50

PROXY_USER = "PKJ9PDmYA1o6zEnL"
PROXY_PASS = "8HGyOYLP3n3m7AVm"
PROXY_HOST = "geo.iproyal.com"
PORTS = list(range(12321, 12331))

ssl._create_default_https_context = ssl._create_unverified_context

UA_STRINGS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/118 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/118 Safari/537.36",
]

def log(msg):
    t = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(t)
    with open(LOG, "a") as f: f.write(t + "\n")

def read(path, default): 
    try: return json.load(open(path))
    except: return default

def write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f: json.dump(data, f, indent=2)
    os.replace(tmp, path)

def proxy(i):
    port = PORTS[i % len(PORTS)]
    return f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{port}"

async def check(browser, url, idx):
    ctx = await browser.new_context(
        user_agent=random.choice(UA_STRINGS),
        proxy={"server": proxy(idx)} if USE_PROXIES else None,
        viewport={"width": 1280, "height": 900}
    )
    page = await ctx.new_page()

    try:
        await page.goto(url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
        html = (await page.content()).lower()

        # ✅ Active keywords
        active_keys = [
            "add to cart", "buy it now", "watchlist", "place bid", "best offer",
            "x-price-primary", "prcIsum".lower()
        ]
        if any(k in html for k in active_keys):
            return "active"

        # ❌ Sold keywords
        sold_keys = [
            "listing has ended", "listing was ended", "no longer available",
            "ended by the seller", "sold"
        ]
        if any(k in html for k in sold_keys):
            return "sold"

        return "sold"  # aggressive default

    except:
        return "sold"  # any failure = sold
    finally:
        await ctx.close()

async def process(browser, chunk, active, sold):
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def worker(i, item):
        async with sem:
            url = item.get("url")
            if not url:
                sold.append(item); return

            status = await check(browser, url, i)
            if status == "active":
                active.append(item)
            else:
                item["sold_at"] = datetime.now().isoformat()
                sold.append(item)
                log(f"SOLD: {item.get('title','')[:80]}")

    await asyncio.gather(*(worker(i,it) for i,it in enumerate(chunk)))

async def main():
    log("🚀 Aggressive verifier started")

    items = read(ITEMS, [])
    sold_hist = read(SOLD, [])
    active, sold = [], []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        chunks = [items[i:i+BATCH] for i in range(0, len(items), BATCH)]

        for chunk in chunks:
            await process(browser, chunk, active, sold)
            sold_hist.extend(sold)

            write(ITEMS, active)
            write(SOLD, sold_hist)
            write(URLS, [x["url"] for x in active])

            log(f"Batch done: active={len(active)}, sold={len(sold_hist)}")

        await browser.close()

    log(f"✅ DONE | Active={len(active)} | Sold={len(sold_hist)}")

if __name__ == "__main__":
    asyncio.run(main())
