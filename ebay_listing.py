import requests
import json
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv("/Users/stephentaykor/Desktop/flipper_Simulation/Flipper_AI/.env")
EBAY_APP_ID = os.getenv("EBAY_CLIENT_ID")  # Change to EBAY_CLIENT_ID
if not EBAY_APP_ID:
    print("Error: EBAY_CLIENT_ID not found in .env file")
    exit(1)

print(f"Using EBAY_APP_ID: {EBAY_APP_ID}")

# Comment out the entire Finding API section (from import to the first exit(1))
"""
endpoint = "https://svcs.ebay.com/services/search/FindingService/v1"
params = {
    "OPERATION-NAME": "findItemsByKeywords",
    "SERVICE-VERSION": "1.0.0",
    "SECURITY-APPNAME": EBAY_APP_ID,
    "RESPONSE-DATA-FORMAT": "JSON",
    "REST-PAYLOAD": "",
    "keywords": "laptop",
    "paginationInput.entriesPerPage": "50"
}

try:
    print(f"Making request to: {endpoint}")
    response = requests.get(endpoint, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    print(f"API response: {json.dumps(data, indent=2)[:500]}...")  # Log first 500 chars
except Exception as e:
    print(f"API request failed: {e}")
    exit(1)

items = []
search_results = data.get("findItemsByKeywordsResponse", [])[0].get("searchResult", [])[0].get("item", [])
for item in search_results:
    item_info = {
        "title": item.get("title", [None])[0],
        "price": item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0].get("__value__", None),
        "currency": item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0].get("@currencyId", None),
        "category": item.get("primaryCategory", [{}])[0].get("categoryName", [None])[0],
        "itemId": item.get("itemId", [None])[0],
        "viewItemURL": item.get("viewItemURL", [None])[0],
        "galleryURL": item.get("galleryURL", [None])[0],
        "location": item.get("location", [None])[0],
        "condition": item.get("condition", [{}])[0].get("conditionDisplayName", [None])[0],
        "listingType": item.get("listingInfo", [{}])[0].get("listingType", [None])[0],
        "sellerUserName": item.get("sellerInfo", [{}])[0].get("sellerUserName", [None])[0],
        "shippingType": item.get("shippingInfo", [{}])[0].get("shippingType", [None])[0],
        "shippingServiceCost": item.get("shippingInfo", [{}])[0].get("shippingServiceCost", [{}])[0].get("__value__", None),
        "shippingCurrency": item.get("shippingInfo", [{}])[0].get("shippingServiceCost", [{}])[0].get("@currencyId", None),
        "country": item.get("country", [None])[0],
        "startTime": item.get("listingInfo", [{}])[0].get("startTime", [None])[0],
        "endTime": item.get("listingInfo", [{}])[0].get("endTime", [None])[0],
    }
    items.append(item_info)

# Save metadata JSON for all items
base_dir = "/Users/stephentaykor/Desktop/flipper_Simulation/Flipper/Flipper/ebay_images"
json_dir = os.path.join(base_dir, "json")
os.makedirs(json_dir, exist_ok=True)

for item in items:
    title = item.get("title", "unknown_item")
    item_id = item.get("itemId", "unknown_id")
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:50]
    json_filename = f"{safe_title}_{item_id}.json"
    json_path = os.path.join(json_dir, json_filename)
    with open(json_path, "w") as f:
        json.dump(item, f, indent=2)
    print(f"Saved metadata for {title} to {json_path}")
"""

# Load token for Browse API
token_env_path = '/Users/stephentaykor/Desktop/flipper_Simulation/Flipper/Flipper/Token.env'
print(f"Loading token from: {token_env_path}")
load_dotenv(token_env_path)
token = os.getenv('EBAY_OAUTH_TOKEN')
print(f"Token loaded: {token[:50] if token else 'None'}...")  # Print first 50 chars for safety
if not token:
    print("Error: EBAY_OAUTH_TOKEN not found in Token.env")
    exit(1)

# Use Browse API
url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
headers = {
    "Authorization": f"Bearer {token}",
    "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
}
params = {"q": "laptop", "limit": 50}

try:
    print(f"Making request to: {url}")
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    print(f"API response: {json.dumps(data, indent=2)[:500]}...")  # Log first 500 chars
except Exception as e:
    print(f"API request failed: {e}")
    exit(1)

items = []
search_results = data.get("itemSummaries", [])
for item in search_results:
    item_info = {
        "title": item.get("title"),
        "price": item.get("price", {}).get("value"),
        "currency": item.get("price", {}).get("currency"),
        "category": item.get("categories", [{}])[0].get("categoryName"),
        "itemId": item.get("itemId"),
        "viewItemURL": item.get("itemWebUrl"),
        "galleryURL": item.get("image", {}).get("imageUrl"),
        "location": item.get("itemLocation", {}).get("country"),
        "condition": item.get("condition"),
        "listingType": item.get("buyingOptions", [""])[0],
        "sellerUserName": item.get("seller", {}).get("username"),
        "shippingType": item.get("shippingOptions", [{}])[0].get("shippingServiceCode"),
        "shippingServiceCost": item.get("shippingOptions", [{}])[0].get("shippingCost", {}).get("value"),
        "shippingCurrency": item.get("shippingOptions", [{}])[0].get("shippingCost", {}).get("currency"),
        "country": item.get("itemLocation", {}).get("country"),
        "startTime": item.get("itemCreationDate"),
        "endTime": item.get("itemEndDate"),
    }
    items.append(item_info)

# Save metadata JSON for all items
base_dir = "/Users/stephentaykor/Desktop/flipper_Simulation/Flipper/Flipper/ebay_images"
json_dir = os.path.join(base_dir, "json")
os.makedirs(json_dir, exist_ok=True)

for item in items:
    title = item.get("title", "unknown_item")
    item_id = item.get("itemId", "unknown_id")
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:50]
    json_filename = f"{safe_title}_{item_id}.json"
    json_path = os.path.join(json_dir, json_filename)
    with open(json_path, "w") as f:
        json.dump(item, f, indent=2)
    print(f"Saved metadata for {title} to {json_path}")

# Test Browse API (already in the code)
