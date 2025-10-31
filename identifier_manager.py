import os
import json
import csv
from datetime import datetime

BASE_DIR = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe"
MASTER_FILE = f"{BASE_DIR}/identifiers_master.json"
CSV_EXPORT = f"{BASE_DIR}/rocket_upload.csv"

os.makedirs(BASE_DIR, exist_ok=True)

def load_master():
    if not os.path.exists(MASTER_FILE):
        return {}
    try:
        with open(MASTER_FILE, "r") as f:
            return {i["item_id"]: i for i in json.load(f)}
    except:
        return {}

def save_master(data_dict):
    data_list = list(data_dict.values())
    with open(MASTER_FILE, "w") as f:
        json.dump(data_list, f, indent=2)
    print(f"✅ Master updated — {len(data_list)} total items")

def add_identifiers(new_items):
    master = load_master()

    for item in new_items:
        item_id = item.get("item_id")
        if not item_id:
            continue

        item["timestamp"] = datetime.now().isoformat()
        master[item_id] = item

    save_master(master)

def export_csv_for_rocket():
    master = load_master()
    with open(CSV_EXPORT, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["identifier", "identifier_type", "item_id"])

        for item in master.values():
            iid = item.get("item_id")
            upc = item.get("upc")
            ean = item.get("ean")
            isbn = item.get("isbn")

            if upc:
                writer.writerow([upc, "UPC", iid])
            if ean:
                writer.writerow([ean, "EAN", iid])
            if isbn:
                writer.writerow([isbn, "ISBN", iid])

    print(f"📤 RocketSauce CSV ready: {CSV_EXPORT}")
