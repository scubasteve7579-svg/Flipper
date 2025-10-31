import json
import os
from collections import defaultdict
from datetime import datetime

# Paths
SOLD_ITEMS_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_recent/sold_items.json"
ACTIVE_ITEMS_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_recent/items.json"
KEEPA_SOLD_DATA = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/keepa_sold_data.json"
OUTPUT_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_recent/scored_combined_items.json"

# Load data
sold_items = []
if os.path.exists(SOLD_ITEMS_FILE):
    with open(SOLD_ITEMS_FILE, 'r') as f:
        sold_items = json.load(f)

active_items = []
if os.path.exists(ACTIVE_ITEMS_FILE):
    with open(ACTIVE_ITEMS_FILE, 'r') as f:
        active_items = json.load(f)

keepa_items = []
if os.path.exists(KEEPA_SOLD_DATA):
    with open(KEEPA_SOLD_DATA, 'r') as f:
        keepa_items = json.load(f)

# Combine sold and keepa data for learning
all_sold = sold_items + keepa_items
category_trends = defaultdict(lambda: {"total_profit": 0, "count": 0, "avg_profit": 0, "sales_volume": 0, "avg_duration": 0})

for item in all_sold:
    if item.get("sold") or ("sold_price" in item and item.get("sold_price")):  # Handle both formats
        category = item.get("categoryPath", "").lower()
        profit = float(item.get("sold_price", 0)) - float(item.get("price", 0)) if "price" in item else 0
        duration = int(item.get("duration", "1 day").split()[0]) if item.get("duration") else 1
        count = 1  # Assume 1 sale per item from sold_items
        if "keepa_sold_data" in item.get("url", ""):  # Keepa data
            count = sum(1 for entry in keepa_items if entry["item_id"] == item["item_id"])  # Approx volume
        category_trends[category]["total_profit"] += profit
        category_trends[category]["count"] += count
        category_trends[category]["sales_volume"] += count
        category_trends[category]["avg_duration"] += duration

for cat, data in category_trends.items():
    if data["count"] > 0:
        data["avg_profit"] = data["total_profit"] / data["count"]
        data["avg_duration"] = data["avg_duration"] / data["count"]

# Score active items using enhanced trends
scored_active = []
for item in active_items:
    category = item.get("categoryPath", "").lower()
    trend = category_trends.get(category, {"total_profit": 0, "count": 0, "avg_profit": 0, "sales_volume": 0, "avg_duration": 0})
    
    # Estimate profit with trend or 30% margin fallback
    estimated_profit = trend["avg_profit"] or (float(item.get("price", 0)) * 0.3)
    
    # Confidence based on volume and duration
    confidence = 0.5
    if trend["sales_volume"] > 5:  # High sales volume boosts confidence
        confidence += 0.2
    if trend["avg_duration"] < 7:  # Faster sales = higher confidence
        confidence += 0.1
    if "electronics" in category or "laptops" in category:
        confidence = min(0.9, confidence + 0.1)  # Cap at 0.9
    
    score = estimated_profit * confidence
    item["profit"] = estimated_profit
    item["confidence"] = confidence
    item["score"] = score
    item["flip_potential"] = "high" if score > 100 else "medium" if score > 50 else "low"
    item["predicted_duration"] = f"{int(trend['avg_duration'])} days" if trend["count"] > 0 else "7 days"
    scored_active.append(item)

# Combine and save (growing feed)
combined_scored = all_sold + scored_active
with open(OUTPUT_FILE, 'w') as f:
    json.dump(combined_scored, f, indent=2)

print(f"✅ Scored {len(scored_active)} active items using trends from {len(all_sold)} sold items. Combined feed saved to {OUTPUT_FILE}.")