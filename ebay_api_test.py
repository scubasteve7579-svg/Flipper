import requests
import os
from dotenv import load_dotenv

load_dotenv("/Users/stephentaykor/Desktop/flipper_Simulation/Flipper_AI/.env")
EBAY_APP_ID = os.getenv("EBAY_APP_ID")
if not EBAY_APP_ID:
    print("Error: EBAY_APP_ID not found in .env file")
    exit(1)

endpoint = "https://svcs.ebay.com/services/search/FindingService/v1"
params = {
    "OPERATION-NAME": "findItemsByKeywords",
    "SERVICE-VERSION": "1.0.0",
    "SECURITY-APPNAME": EBAY_APP_ID,
    "RESPONSE-DATA-FORMAT": "JSON",
    "REST-PAYLOAD": "",
    "keywords": "test"
}

try:
    print(f"Testing eBay API key: {EBAY_APP_ID}")
    response = requests.get(endpoint, params=params, timeout=10)
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        print("API key is activated and working!")
        print("Sample response:", response.text[:500], "...")
    else:
        print("API key may not be activated or there is another issue.")
        print("Response:", response.text[:500], "...")
except Exception as e:
    print(f"API request failed: {e}")