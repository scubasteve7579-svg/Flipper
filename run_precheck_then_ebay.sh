#!/usr/bin/env bash
set -e
BASE="/Users/stephentaykor/Desktop/flipper_Simulation/Flipper/Flipper"
VENV="/Users/stephentaykor/Desktop/flipper_Simulation/.venv"

source "${VENV}/bin/activate"
python3 "${BASE}/rocket_precheck_and_upload.py"
if [ $? -eq 0 ]; then
  echo "✅ Rocket precheck OK — starting ebay_scraping_recent.py"
  python3 "${BASE}/ebay_scraping_recent.py"
else
  echo "⛔ Rocket precheck failed — not starting ebay_scraping_recent.py"
  exit 1
fi
