import subprocess
import sys
import os
import threading
import time
import json

# Paths to scripts (update if needed)
SCRAPER_SCRIPT = "/Users/stephentaykor/Desktop/flipper_Simulation/Flipper/Flipper/ebay_scraping_recent.py"
VERIFIER_SCRIPT = "/Users/stephentaykor/Desktop/flipper_Simulation/Flipper/Flipper/verify_url.py"
SCORER_SCRIPT = "/Users/stephentaykor/Desktop/flipper_Simulation/Flipper/Flipper/Score_Real_items.py"
COMBINED_ITEMS_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/combined_items.json"
SAFE_ITEMS_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/items.json"
RECENT_ITEMS_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_recent/items.json"

def run_script(script_path, description):
    print(f"🚀 Running {description}...")
    try:
        result = subprocess.run([sys.executable, script_path], capture_output=False, text=True)
        if result.returncode != 0:
            print(f"❌ {description} failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
        else:
            print(f"✅ {description} completed successfully.")
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False
    return True

def combine_items():
    print("🔗 Combining items from both sources...")
    items = []
    for path in [SAFE_ITEMS_FILE, RECENT_ITEMS_FILE]:
        if os.path.exists(path):
            with open(path, "r") as f:
                try:
                    items.extend(json.load(f))
                except Exception as e:
                    print(f"⚠️ Could not load {path}: {e}")
    # Deduplicate by item_id
    seen = set()
    deduped = []
    for item in items:
        iid = item.get("item_id")
        if iid and iid not in seen:
            seen.add(iid)
            deduped.append(item)
    with open(COMBINED_ITEMS_FILE, "w") as f:
        json.dump(deduped, f, indent=2)
    print(f"✅ Combined {len(deduped)} unique items.")

def main():
    print("🔄 Starting full pipeline: Scraper → Verifier → Combine → Scorer")
    
    # Step 1: Run Scraper
    if not run_script(SCRAPER_SCRIPT, "Scraper (ebay_scraping_recent.py)"):
        print("❌ Pipeline stopped at scraper.")
        return
    
    # Step 2: Run Verifier
    if not run_script(VERIFIER_SCRIPT, "Verifier (verify_url.py)"):
        print("❌ Pipeline stopped at verifier.")
        return

    # Step 3: Combine items from both sources
    combine_items()
    
    # Step 4: Run Scorer on combined items
    if not run_script(COMBINED_ITEMS_FILE, "Scorer (Score_Real_items.py)"):
        print("❌ Pipeline stopped at scorer.")
        return
    
    print("🎉 Full pipeline completed! Items scraped, verified, combined, and scored.")

if __name__ == "__main__":
    main()