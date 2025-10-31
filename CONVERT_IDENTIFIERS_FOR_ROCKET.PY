import json, re, csv, os
from pathlib import Path

input_file = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/ebay_item_identifiers.json"
output_json = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/rocket_input.json"
output_csv = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/rocket_input.csv"

def extract_brand(title):
    if not title: return None
    brands = ["Apple", "JBL", "Harman Kardon", "Sony", "Bose", "Samsung", "Dell", "HP", "Lenovo"]
    for b in brands:
        if b.lower() in title.lower():
            return b
    # fallback: first word before space if likely brand-like
    first = title.split()[0]
    return first if first.istitle() else None

def extract_ean(item_id):
    try:
        parts = item_id.split("|")
        tail = parts[-1]
        if tail.isdigit() and len(tail) in (12, 13):
            return tail
    except:
        pass
    return None

with open(input_file, "r") as f:
    data = json.load(f)

records = []
for item in data:
    ean = extract_ean(item.get("item_id",""))
    brand = item.get("brand") or extract_brand(item.get("title", ""))

    rec = {
        "source": "ebay",
        "item_id": item.get("item_id"),
        "title": item.get("title"),
        "brand": brand,
        "upc": item.get("upc"),
        "ean": ean,
    }
    records.append(rec)

print(f"✅ Parsed {len(records)} records")

# Save JSON
with open(output_json, "w") as f:
    json.dump(records, f, indent=2)

# Save CSV
with open(output_csv, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=records[0].keys())
    writer.writeheader()
    writer.writerows(records)

print(f"✅ Saved JSON → {output_json}")
print(f"✅ Saved CSV →  {output_csv}")
print("🎯 Ready for RocketSource upload!")
