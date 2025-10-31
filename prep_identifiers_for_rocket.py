import json, csv, os

BASE_DIR = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe"
INPUT_FILE = f"{BASE_DIR}/ebay_item_identifiers.json"

MASTER_JSON = f"{BASE_DIR}/identifiers_master.json"
ROCKET_JSON = f"{BASE_DIR}/rocket_upload.json"
ROCKET_CSV  = f"{BASE_DIR}/rocket_upload.csv"

print("📦 Loading eBay identifiers...")

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(f"Input file missing: {INPUT_FILE}")

with open(INPUT_FILE, "r") as f:
    raw_data = json.load(f)

print(f"✅ Loaded {len(raw_data)} raw records")

# Deduplicate by item_id
master = {}
for item in raw_data:
    iid = item.get("item_id")
    if not iid:
        continue
    master[iid] = {
        "item_id": iid,
        "title": (item.get("title") or "")[:200],  # trim to safe length
        "brand": item.get("brand"),
        "mpn": item.get("mpn"),
        "gtin": item.get("gtin"),
        "upc": item.get("upc"),
        "ean": item.get("ean"),
    }

master_list = list(master.values())
print(f"✅ Deduped to {len(master_list)} unique items")

# Save master JSON archive
with open(MASTER_JSON, "w") as f:
    json.dump(master_list, f, indent=2)
print(f"💾 Master saved → {MASTER_JSON}")

# Save Rocket JSON (minimal formatting)
with open(ROCKET_JSON, "w") as f:
    json.dump(master_list, f, separators=(",", ":"))
print(f"🚀 Rocket JSON ready → {ROCKET_JSON}")

# Save CSV
with open(ROCKET_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["item_id","title","brand","mpn","gtin","upc","ean"])
    writer.writeheader()
    for row in master_list:
        writer.writerow(row)

print(f"🧾 Rocket CSV ready → {ROCKET_CSV}")

print("🎉 Conversion complete — awaiting RocketSauce upload format")
