import asyncio
import json
import os
import time
import random
import base64
import ssl
from datetime import datetime
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
import requests

# Load environment
load_dotenv("/Users/stephentaykor/Desktop/flipper_Simulation/Flipper_AI/.env")

EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
EBAY_REFRESH_TOKEN = os.getenv("EBAY_REFRESH_TOKEN")
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

# Flipper-specific paths
SAFE_ITEMS_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/items.json"
RECENT_ITEMS_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_recent/items.json"
SOLD_ITEMS_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/sold_items.json"
ITEMS_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/items.json"
SCORING_PATH = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/scoring.json"
URLS_PATH = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/urls.json"
LOG_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/verifier.log"

# User agents
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

MAX_RETRIES = 3
BATCH_SIZE = 10  # Process 10 items per batch
REQUESTS_PER_SECOND_PER_IP = 5  # Safe rate per IP
MAX_ITEMS_2GB = 40000  # Approx. 2GB limit

# IPRoyal proxy pool
PROXY_USER = "PKJ9PDmYA1o6zEnL"
PROXY_PASS = "8HGyOYLP3n3m7AVm"
PROXY_HOST = "geo.iproyal.com"
PROXY_PORTS = list(range(12321, 12331))  # Ports 12321 to 12330

def get_rotated_proxy(index):
    """Return a proxy URL with a unique port for each index."""
    port = PROXY_PORTS[index % len(PROXY_PORTS)]
    return f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{port}"

# Bypass SSL certificate verification
ssl._create_default_https_context = ssl._create_unverified_context

# === Helpers ===
def log_progress(message):
    """Log progress to file and print to terminal."""
    print(message, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()}: {message}\n")

def refresh_token():
    """Refresh eBay OAuth token for Flipper."""
    creds = base64.b64encode(f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode()).decode()
    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Authorization": f"Basic {creds}"},
        data={"grant_type": "refresh_token", "refresh_token": EBAY_REFRESH_TOKEN, "scope": "https://api.ebay.com/oauth/api_scope"}
    )
    if resp.status_code == 200:
        log_progress("🔑 Refreshed token")
        return resp.json()["access_token"]
    log_progress(f"❌ Token refresh failed: {resp.text}")
    return None

def is_flipper_data(file_path):
    """Ensure we're only processing Flipper-specific data."""
    return file_path.startswith("/Users/stephentaykor/Desktop/flipper_Simulation/")

def save_items(file_path, items):
    """Save items to a JSON file, appending and deduping."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    existing_items = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            existing_items = json.load(f)
    combined = {item["item_id"]: item for item in existing_items + items}.values()
    with open(file_path, 'w') as f:
        json.dump(list(combined), f, indent=2)

# === Core Functions ===
async def check_url_selenium(driver, url, proxy_url):
    """Fast verify URL status and price using Selenium."""
    if not url or not url.startswith("https://www.ebay.com/itm/"):
        return (False, None)
    options = Options()
    options.add_argument(f"--proxy-server={proxy_url}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.headless = True
    # Bypass SSL errors
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--ignore-certificate-errors-spki-list")
    options.add_argument("--ignore-ssl-errors-ignore-untrusted")
    options.add_argument("--allow-running-insecure-content")
    service = Service(executable_path="/Users/stephentaykor/Downloads/chrome-mac-arm64/chromedriver")
    for attempt in range(MAX_RETRIES):
        try:
            driver = uc.Chrome(service=service, options=options)
            driver.set_page_load_timeout(15)
            driver.set_script_timeout(15)
            driver.get(url)
            if "Pardon Our Interruption" in driver.page_source or "Checking your browser" in driver.page_source:
                driver.quit()
                return ("bot_detected", None)
            sold_elems = driver.find_elements(By.XPATH, "//span[contains(text(), 'Sold')] | //div[contains(@class, 'sold')] | //span[contains(text(), 'Ended')]")
            if sold_elems:
                price_elems = driver.find_elements(By.CSS_SELECTOR, ".s-item__price")
                price = None
                if price_elems:
                    price_text = price_elems[0].text.replace("$", "").replace(",", "").strip()
                    price = float(price_text) if price_text.replace(".", "").isdigit() else None
                driver.quit()
                return ("sold", price)
            else:
                driver.quit()
                return ("active", None)
        except (NoSuchElementException, TimeoutException, WebDriverException):
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)
                continue
            return (False, None)
    return ("bot_detected", None)

async def verify_and_clean_items():
    """Verify and clean items, separating sold and active listings."""
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
    active_items = []
    batch_sold_count = 0
    batch_active_count = 0
    batch_inaccessible_count = 0
    items_processed = 0

    for i in range(0, len(items), BATCH_SIZE):
        if items_processed >= MAX_ITEMS_2GB:
            log_progress(f"Reached 2GB limit (~{MAX_ITEMS_2GB} items), pausing verification")
            print(f"Reached 2GB limit (~{MAX_ITEMS_2GB} items), pausing verification")
            break

        batch = items[i:i+BATCH_SIZE]
        tasks = []
        for j, item in enumerate(batch):
            url = item.get("url")
            if url and isinstance(url, str):
                tasks.append(check_url_selenium(None, url, get_rotated_proxy(j)))
            else:
                tasks.append(asyncio.to_thread(lambda: (False, None)))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for j, result in enumerate(results):
            item = batch[j]
            items_processed += 1
            log_progress(f"Checking item {i+j+1}/{len(items)}: {item.get('title', 'No title')} (URL: {item.get('url', 'No URL')})")
            print(f"Checking item {i+j+1}/{len(items)}: {item.get('title', 'No title')} (URL: {item.get('url', 'No URL')})")

            if isinstance(result, Exception):
                status, sold_price = (False, None)
                log_progress(f"Error processing {item.get('title', 'No title')}: {repr(result)}")
            else:
                status, sold_price = result

            if status == "sold":
                item["sold"] = True
                item["sold_price"] = sold_price
                sold_items.append(item)
                batch_sold_count += 1
                log_progress(f"Sold item detected: {item.get('title', 'No title')} (Price: {sold_price}, URL: {item.get('url', 'No URL')})")
                print(f"Sold item detected: {item.get('title', 'No title')} (Price: {sold_price}, URL: {item.get('url', 'No URL')})")
            elif status == "active":
                item["sold"] = False
                active_items.append(item)
                batch_active_count += 1
                log_progress(f"Active item: {item.get('title', 'No title')} (URL: {item.get('url', 'No URL')})")
                print(f"Active item: {item.get('title', 'No title')} (URL: {item.get('url', 'No URL')})")
            else:  # bot_detected or error
                item["sold"] = "unknown"
                sold_items.append(item)
                batch_inaccessible_count += 1
                log_progress(f"Inaccessible or bot-detected: {item.get('title', 'No title')} (URL: {item.get('url', 'No URL')})")
                print(f"Inaccessible or bot-detected: {item.get('title', 'No title')} (URL: {item.get('url', 'No URL')})")

        log_progress(f"Batch {i+1}-{i+len(batch)}: {batch_sold_count} sold, {batch_active_count} active, {batch_inaccessible_count} inaccessible")
        print(f"Batch {i+1}-{i+len(batch)}: {batch_sold_count} sold, {batch_active_count} active, {batch_inaccessible_count} inaccessible")

        # Save periodically
        if (i + 1) % BATCH_SIZE == 0 or i == len(items) - 1 or items_processed >= MAX_ITEMS_2GB:
            save_items(ITEMS_FILE, active_items)
            existing_sold_ids = {item.get("item_id") for item in sold_items if item.get("item_id")}
            new_sold = [item for item in sold_items if item.get("item_id") not in existing_sold_ids]
            with open(SOLD_ITEMS_FILE, 'w') as f:
                json.dump(sold_items, f, indent=2)
            save_items(SCORING_PATH, active_items)
            urls = [item["url"] for item in active_items if item.get("url")]
            with open(URLS_PATH, 'w') as f:
                json.dump(urls, f, indent=2)
            log_progress(f"💾 Saved batch {i+1}: {len(active_items)} active, {len(new_sold)} new sold to {ITEMS_FILE}, {SOLD_ITEMS_FILE}, {SCORING_PATH}, {URLS_PATH}")
            print(f"💾 Saved batch {i+1}: {len(active_items)} active, {len(new_sold)} new sold to {ITEMS_FILE}, {SOLD_ITEMS_FILE}, {SCORING_PATH}, {URLS_PATH}")

        await asyncio.sleep(random.uniform(5, 10))  # Random delay between batches

    log_progress(f"Verifier complete: {len(sold_items)} sold/inaccessible items found, {len(active_items)} active items found")
    print(f"Verifier complete: {len(sold_items)} sold/inaccessible items found, {len(active_items)} active items found")

if __name__ == "__main__":
    while True:
        asyncio.run(verify_and_clean_items())
        print("Verifier sleeping for 5 minutes before next check...")
        time.sleep(300)  # Sleep 5 minutes, then restart