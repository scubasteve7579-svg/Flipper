import asyncio
import json
import os
import time
import random
import base64
import ssl
from datetime import datetime
from dotenv import load_dotenv
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException

# ────────────────────────────────────────────────────────────────
# Load environment
# ────────────────────────────────────────────────────────────────
load_dotenv("/Users/stephentaykor/Desktop/flipper_Simulation/Flipper_AI/.env")

EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
EBAY_REFRESH_TOKEN = os.getenv("EBAY_REFRESH_TOKEN")
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

# ────────────────────────────────────────────────────────────────
# File paths
# ────────────────────────────────────────────────────────────────
BASE_DIR = "/Users/stephentaykor/Desktop/flipper_Simulation"
SAFE_ITEMS_FILE = f"{BASE_DIR}/my_items_safe/items.json"
RECENT_ITEMS_FILE = f"{BASE_DIR}/my_items_recent/items.json"
SOLD_ITEMS_FILE = f"{BASE_DIR}/my_items_safe/sold_items.json"
ITEMS_FILE = f"{BASE_DIR}/my_items_safe/items.json"
SCORING_PATH = f"{BASE_DIR}/my_items_safe.json"
URLS_PATH = f"{BASE_DIR}/my_items_safe/urls.json"
LOG_FILE = f"{BASE_DIR}/my_items_safe/verifier.log"

# ────────────────────────────────────────────────────────────────
# Settings
# ────────────────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
]
MAX_RETRIES = 3
BATCH_SIZE = 10
CONCURRENCY = 10

# Proxy rotation (IPRoyal)
PROXY_USER = "PKJ9PDmYA1o6zEnL"
PROXY_PASS = "8HGyOYLP3n3m7AVm"
PROXY_HOST = "geo.iproyal.com"
PROXY_PORTS = list(range(12321, 12331))

def get_rotated_proxy(index: int) -> str:
    port = PROXY_PORTS[index % len(PROXY_PORTS)]
    return f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{port}"

ssl._create_default_https_context = ssl._create_unverified_context

# ────────────────────────────────────────────────────────────────
# Utility functions
# ────────────────────────────────────────────────────────────────
def log_progress(message: str):
    print(message, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()}: {message}\n")

def refresh_token():
    creds = base64.b64encode(f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode()).decode()
    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Authorization": f"Basic {creds}"},
        data={
            "grant_type": "refresh_token",
            "refresh_token": EBAY_REFRESH_TOKEN,
            "scope": "https://api.ebay.com/oauth/api_scope"
        }
    )
    if resp.status_code == 200:
        log_progress("🔑 Refreshed token")
        return resp.json()["access_token"]
    log_progress(f"❌ Token refresh failed: {resp.text}")
    return None

def is_flipper_data(path):
    return path.startswith(BASE_DIR)

def save_items(file_path, items):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    existing = []
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    combined = {i["item_id"]: i for i in existing + items}.values()
    with open(file_path, "w") as f:
        json.dump(list(combined), f, indent=2)

# ────────────────────────────────────────────────────────────────
# Selenium Core (Stable)
# ────────────────────────────────────────────────────────────────
# def check_url_selenium(url, proxy_url):
#     """Stable ChromeDriver-based item status check."""
#     if not url.startswith("https://www.ebay.com/itm/"):
#         return (False, None)

#     driver_path = "/Users/stephentaykor/Downloads/chromedriver-mac-arm64/chromedriver"
#     os.chmod(driver_path, 0o755)

#     for attempt in range(MAX_RETRIES):
#         driver = None
#         try:
#             options = Options()
#             options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
#             options.add_argument("--headless=new")
#             options.add_argument("--disable-gpu")
#             options.add_argument("--no-sandbox")
#             options.add_argument("--disable-dev-shm-usage")
#             options.add_argument("--disable-extensions")
#             options.add_argument("--blink-settings=imagesEnabled=false")
#             options.add_argument("--ignore-certificate-errors")
#             options.add_argument("--disable-background-networking")
#             options.add_argument("--disable-default-apps")
#             options.add_argument("--no-first-run")
#             options.add_argument(f"--proxy-server={proxy_url}")
#             options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
#             prefs = {
#                 "profile.managed_default_content_settings.images": 2,
#                 "profile.default_content_setting_values.notifications": 2,
#                 "profile.managed_default_content_settings.stylesheets": 2,
#             }
#             options.add_experimental_option("prefs", prefs)

#             service = Service(driver_path)
#             driver = webdriver.Chrome(service=service, options=options)
#             driver.set_page_load_timeout(20)
#             driver.set_script_timeout(20)
#             print(f"Starting driver for {url} (attempt {attempt+1})")
#             driver.get(url)
#             print(f"Page loaded for {url}")

#             # Bot detection
#             if "Pardon Our Interruption" in driver.page_source or "Checking your browser" in driver.page_source:
#                 print("Bot detection page encountered.")
#                 return ("bot_detected", None)

#             # Ended/cancelled
#             if "This listing was ended" in driver.page_source or "This listing has ended" in driver.page_source:
#                 return ("ended", None)

#             # Sold check
#             sold_elems = driver.find_elements(By.XPATH, "//span[contains(text(), 'Sold')] | //div[contains(@class, 'sold')] | //span[contains(text(), 'Ended')]")
#             if sold_elems:
#                 price_elems = driver.find_elements(By.CSS_SELECTOR, ".s-item__price")
#                 price = None
#                 if price_elems:
#                     price_text = price_elems[0].text.replace("$", "").replace(",", "").strip()
#                     try:
#                         price = float(price_text)
#                     except Exception:
#                         price = None
#                 return ("sold", price)
#             else:
#                 # Wait for price to appear (active listing)
#                 try:
#                     WebDriverWait(driver, 10).until(
#                         EC.presence_of_element_located((By.CSS_SELECTOR, ".s-item__price"))
#                     )
#                 except TimeoutException:
#                     pass
#                 return ("active", None)
#         except (TimeoutException, NoSuchElementException, WebDriverException) as e:
#             print(f"⚠️ Attempt {attempt+1} failed for {url}: {e}")
#             if driver:
#                 print("---- PAGE SOURCE (truncated) ----")
#                 print(driver.page_source[:1000])
#                 print("---- END PAGE SOURCE ----")
#             if attempt < MAX_RETRIES - 1:
#                 time.sleep(random.uniform(3, 6))
#                 continue
#             return (False, None)
#         finally:
#             if driver:
#                 driver.quit()
#                 print(f"Driver quit for {url}")
#     return ("bot_detected", None)

async def limited_check_url(url, proxy_url, semaphore):
    async with semaphore:
        # Placeholder: always return ("active", None)
        # Replace this with your Playwright logic later
        print(f"Playwright placeholder for {url} with proxy {proxy_url}")
        await asyncio.sleep(0.1)
        return ("active", None)

async def verify_and_clean_items(max_retries=5):
    log_progress("Starting verifier")
    print(f"🚀 Starting verifier (NZDT: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Validate Flipper-specific paths
    if not all(is_flipper_data(path) for path in [SAFE_ITEMS_FILE, RECENT_ITEMS_FILE, ITEMS_FILE, SOLD_ITEMS_FILE, SCORING_PATH, URLS_PATH]):
        log_progress("Error: Detected non-Flipper data paths, exiting")
        print("Error: Detected non-Flipper data paths, exiting")
        return

    # Load and combine items
    items = []
    for file_path in [SAFE_ITEMS_FILE, RECENT_ITEMS_FILE]:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    file_items = json.load(f)
                    items.extend(file_items)
                    log_progress(f"Loaded {len(file_items)} items from {file_path}")
                    print(f"Loaded {len(file_items)} items from {file_path}")
            else:
                log_progress(f"No file found at {file_path}")
                print(f"No file found at {file_path}")
        except json.JSONDecodeError as e:
            log_progress(f"Error reading {file_path}: {e}")
            print(f"Error reading {file_path}: {e}")
            continue

    if not items:
        log_progress("No items to process, exiting")
        print("No items to process, exiting")
        return

    # Deduplicate on item_id
    seen_ids = set()
    deduped_items = []
    for item in items:
        item_id = item.get("item_id")
        if item_id and item_id not in seen_ids:
            seen_ids.add(item_id)
            deduped_items.append(item)
    items = deduped_items
    log_progress(f"Combined and deduped {len(items)} items")
    print(f"Combined and deduped {len(items)} items")

    # Load existing sold items
    sold_items = []
    try:
        if os.path.exists(SOLD_ITEMS_FILE):
            with open(SOLD_ITEMS_FILE, 'r') as f:
                sold_items = json.load(f)
                log_progress(f"Loaded {len(sold_items)} existing sold items from {SOLD_ITEMS_FILE}")
                print(f"Loaded {len(sold_items)} existing sold items from {SOLD_ITEMS_FILE}")
    except json.JSONDecodeError as e:
        log_progress(f"Error reading {SOLD_ITEMS_FILE}: {e}")
        print(f"Error reading {SOLD_ITEMS_FILE}: {e}")

    # Refresh token
    token = refresh_token()
    if not token:
        log_progress("No valid token, exiting")
        print("No valid token, exiting")
        return

    # Verify items in batches
    retry_count = 0
    items_to_check = items

    while retry_count < max_retries and items_to_check:
        print(f"🔄 Pass {retry_count+1} | Checking {len(items_to_check)} items...")
        active_items = []
        sold_items = []
        inaccessible_items = []
        items_processed = 0

        semaphore = asyncio.Semaphore(CONCURRENCY)
        for i in range(0, len(items_to_check), BATCH_SIZE):
            batch = items_to_check[i:i+BATCH_SIZE]
            print(f"🔢 Batch {i//BATCH_SIZE+1}: Checking items {i+1}-{min(i+BATCH_SIZE, len(items_to_check))} of {len(items_to_check)}")
            tasks = []
            for j, item in enumerate(batch):
                url = item.get("url")
                proxy = get_rotated_proxy(i + j)
                if url and isinstance(url, str):
                    tasks.append(limited_check_url(url, proxy, semaphore))
                else:
                    tasks.append(asyncio.to_thread(lambda: (False, None)))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for j, result in enumerate(results):
                item = batch[j]
                if isinstance(result, Exception):
                    print(f"❌ Exception for item {item.get('item_id')}: {result}")
                    status, sold_price = (False, None)
                else:
                    status, sold_price = result
                print(f"    Processed item {i+j+1}/{len(items_to_check)}: {item.get('title', '')[:40]}... Status: {status}")

                if status == "sold":
                    item["sold"] = True
                    item["sold_price"] = sold_price
                    sold_items.append(item)
                elif status == "active":
                    item["sold"] = False
                    active_items.append(item)
                else:  # bot_detected or error
                    item["sold"] = "unknown"
                    inaccessible_items.append(item)

            await asyncio.sleep(random.uniform(2, 4))  # Shorter sleep for stability

        # Save after each pass
        save_items(ITEMS_FILE, active_items)
        with open(SOLD_ITEMS_FILE, 'w') as f:
            json.dump(sold_items, f, indent=2)
        save_items(SCORING_PATH, active_items)
        urls = [item["url"] for item in active_items if item.get("url")]
        with open(URLS_PATH, 'w') as f:
            json.dump(urls, f, indent=2)

        print(f"Pass {retry_count+1} complete: {len(sold_items)} sold, {len(active_items)} active, {len(inaccessible_items)} inaccessible")
        log_progress(f"Pass {retry_count+1} complete: {len(sold_items)} sold, {len(active_items)} active, {len(inaccessible_items)} inaccessible")

        # Prepare for next retry
        items_to_check = inaccessible_items
        retry_count += 1

    print(f"✅ Verification finished after {retry_count} passes.")
    log_progress(f"Verification finished after {retry_count} passes.")

if __name__ == "__main__":
    try:
        asyncio.run(verify_and_clean_items())
    except Exception as e:
        print(f"❌ Fatal error: {e}")