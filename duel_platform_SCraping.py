import requests
from bs4 import BeautifulSoup
import json
import time
import random
import base64
from dotenv import load_dotenv
import os

# Load .env
load_dotenv("/Users/stephentaykor/Desktop/flipper_Simulation/Flipper_AI/.env")
SCRAPINGDOG_API = os.getenv("SCRAPINGDOG_API")
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
if not SCRAPINGDOG_API or not EBAY_CLIENT_ID or not EBAY_CLIENT_SECRET:
    raise ValueError("Missing API keys in .env! Need SCRAPINGDOG_API, EBAY_CLIENT_ID, EBAY_CLIENT_SECRET")

AMAZON_BASE_URL = f"https://api.scrapingdog.com/scrape?api_key={SCRAPINGDOG_API}"

def get_ebay_token():
    auth_string = base64.b64encode(f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_string}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"}
    try:
        response = requests.post("https://api.ebay.com/identity/v1/oauth2/token", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("access_token")
        print(f"eBay token request failed: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        print(f"eBay token error: {e}")
        return None

EBAY_TOKEN = get_ebay_token()
EBAY_AVAILABLE = bool(EBAY_TOKEN)
EBAY_BASE_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search" if EBAY_AVAILABLE else None

def scrape_amazon_product(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            params = {'url': url, 'render_js': 'false', 'country_code': 'US'}
            response = requests.get(AMAZON_BASE_URL, params=params, timeout=15)
            if response.status_code != 200:
                print(f"Amazon error on {url}: {response.status_code}")
                time.sleep(2 ** attempt)
                continue
            soup = BeautifulSoup(response.text, 'lxml')
            title = soup.select_one('#productTitle')
            title = title.get_text(strip=True) if title else 'N/A'
            price_whole = soup.select_one('.a-price-whole')
            price_fraction = soup.select_one('.a-price-fraction')
            price = f"{price_whole.get_text(strip=True)}.{price_fraction.get_text(strip=True)}" if price_whole and price_fraction else 'N/A'
            asin = url.split('/dp/')[1].split('/')[0] if '/dp/' in url else 'N/A'
            images = [img.get('src') for img in soup.select('#altImages img, #landingImage')[:9] 
                     if img.get('src') and 'amazon.com' in img.get('src')]
            return {
                'platform': 'amazon',
                'title': title,
                'price': price,
                'id': asin,
                'images': images[:1] if images else [],
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'url': url
            }
        except Exception as e:
            print(f"Amazon attempt {attempt + 1} failed for {url}: {e}")
            time.sleep(2 ** attempt)
    return None

def scrape_ebay_product(item_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            if not EBAY_AVAILABLE:
                return None
            url = f"https://api.ebay.com/buy/browse/v1/item/{item_id}"
            headers = {"Authorization": f"Bearer {EBAY_TOKEN}", "Accept": "application/json"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"eBay error on {item_id}: {response.status_code}")
                time.sleep(2 ** attempt)
                continue
            data = response.json()
            title = data.get('title', 'N/A')
            price = data.get('price', {}).get('value', 'N/A')
            currency = data.get('price', {}).get('currency', 'USD')
            images = [data.get('image', {}).get('imageUrl')] if data.get('image') else []
            return {
                'platform': 'ebay',
                'title': title,
                'price': f"{price} {currency}",
                'id': item_id,
                'images': images[:1] if images else [],
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'url': f"https://www.ebay.com/itm/{item_id}"
            }
        except Exception as e:
            print(f"eBay attempt {attempt + 1} failed for {item_id}: {e}")
            time.sleep(2 ** attempt)
    return None

def scrape_amazon_search(query, max_pages=1):
    results = []
    base_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}&rh=p_n_date_first_available_absolute%3A1640995200"
    for page in range(1, max_pages + 1):
        url = f"{base_url}&page={page}"
        print(f"Scraping Amazon page {page}: {url}")
        try:
            params = {'url': url, 'render_js': 'true', 'country_code': 'US'}
            response = requests.get(AMAZON_BASE_URL, params=params, timeout=15)
            if response.status_code != 200:
                print(f"Amazon search page {page} failed: {response.status_code}")
                continue
            soup = BeautifulSoup(response.text, 'lxml')
            products = soup.select('div[data-asin][data-asin!=""]')
            scraped_count = 0
            for prod in products:
                if scraped_count >= 20:  # Cap at 20
                    break
                link = prod.select_one('a.a-link-normal[href*="/dp/"]')
                if link and 'href' in link.attrs:
                    product_url = 'https://www.amazon.com' + link['href']
                    product_data = scrape_amazon_product(product_url)
                    if product_data:
                        results.append(product_data)
                        print(f"Scraped Amazon: {product_data['title'][:50]}...")
                        scraped_count += 1
                        time.sleep(random.uniform(0.5, 1.5))
            print(f"Amazon page {page}: Scraped {scraped_count} items")
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            print(f"Amazon search page {page} failed: {e}")
    return results

def scrape_ebay_search(query, max_entries=100):
    if not EBAY_AVAILABLE:
        print("eBay not available, skipping...")
        return []
    results = []
    headers = {
        "Authorization": f"Bearer {EBAY_TOKEN}",
        "Accept": "application/json"
    }
    params = {
        'q': query,
        'limit': str(min(max_entries, 100)),
        'filter': 'buyingOptions:{FIXED_PRICE|Auction},conditionIds:{1000|1500}',
        'sort': 'endTimeSoonest',
        'aspect_filter': 'categoryIds:{175673}',  # Electronics
        'fieldsets': 'full'
    }
    try:
        print(f"Scraping eBay for '{query}'...")
        response = requests.get(EBAY_BASE_URL, headers=headers, params=params, timeout=15)
        if response.status_code != 200:
            print(f"eBay search failed: {response.status_code} - {response.text}")
            return results
        data = response.json()
        items = data.get('itemSummaries', [])
        print(f"eBay found {len(items)} items")
        scraped_count = 0
        for item in items:
            if scraped_count >= 20:  # Cap at 20 detailed
                break
            item_id = item.get('itemId')
            if item_id:
                product_data = scrape_ebay_product(item_id)
                if product_data:
                    results.append(product_data)
                    print(f"Scraped eBay: {product_data['title'][:50]}...")
                    scraped_count += 1
                    time.sleep(random.uniform(0.5, 1.5))
        print(f"eBay: Processed {scraped_count} detailed items")
        time.sleep(random.uniform(2, 4))
    except Exception as e:
        print(f"eBay search failed: {e}")
    return results

def dual_platform_search(query, amazon_pages=1, ebay_entries=100):
    print(f"🚀 Starting dual-platform search for '{query}'...")
    print(f"📦 Amazon: {amazon_pages} pages | 🛒 eBay: {ebay_entries} entries")
    
    all_results = []
    
    # Amazon search
    print("\n📦 --- AMAZON SEARCH ---")
    amazon_results = scrape_amazon_search(query, max_pages=amazon_pages)
    all_results.extend(amazon_results)
    print(f"✅ Amazon: {len(amazon_results)} items scraped")
    
    # eBay search
    if EBAY_AVAILABLE:
        print("\n🛒 --- EBAY SEARCH ---")
        ebay_results = scrape_ebay_search(query, max_entries=ebay_entries)
        all_results.extend(ebay_results)
        print(f"✅ eBay: {len(ebay_results)} items scraped")
    else:
        print("\n⚠️ eBay: Skipped (token unavailable)")
    
    # Save combined catalog
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    catalog_data = {
        'search_query': query,
        'timestamp': timestamp,
        'total_items': len(all_results),
        'amazon_count': len([r for r in all_results if r['platform'] == 'amazon']),
        'ebay_count': len([r for r in all_results if r['platform'] == 'ebay']),
        'items': all_results
    }
    
    filename = f"flipper_dual_catalog_{timestamp.replace(':', '-').replace(' ', '_')}.json"
    with open(filename, 'w') as f:
        json.dump(catalog_data, f, indent=2)
    
    # Save simple version for Flask
    simple_results = [item for item in all_results if 'title' in item]
    with open('flipper_catalog.json', 'w') as f:
        json.dump(simple_results, f, indent=2)
    
    print(f"\n🎉 SAVED: {filename}")
    print(f"📊 Total: {catalog_data['total_items']} items")
    print(f"📦 Amazon: {catalog_data['amazon_count']} | 🛒 eBay: {catalog_data['ebay_count']}")
    
    return all_results

if __name__ == "__main__":
    print("=== FLIPPER DUAL-PLATFORM SCRAPER ===")
    try:
        query = "electronics"
        results = dual_platform_search(
            query=query,
            amazon_pages=1,
            ebay_entries=100
        )
    except KeyboardInterrupt:
        print("\n⏹️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Script failed: {e}")
        import traceback
        traceback.print_exc()