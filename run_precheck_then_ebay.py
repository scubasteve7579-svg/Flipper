#!/usr/bin/env python3
"""
run_precheck_then_ebay.py
- Loads env
- Performs a multipart upload precheck against RocketSource (v3 preferred)
- If precheck OK -> launches ebay_scraping_recent.py (subprocess)
- Writes a detailed precheck result JSON to OUTPUT_DIR/rocket_upload_test_result.json
"""

import os
import sys
import json
import time
import socket
import tempfile
import logging
import requests
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
from typing import Tuple

# ------- Config -------
BASE_DIR = Path("/Users/stephentaykor/Desktop/flipper_Simulation")
ENV_FILE = BASE_DIR / "Flipper_AI" / ".env"
OUTPUT_DIR = BASE_DIR / "my_items_safe"
IDENTIFIERS_FILE = OUTPUT_DIR / "ebay_item_identifiers.json"
RESULT_FILE = OUTPUT_DIR / "rocket_upload_test_result.json"
LOG_FILE = OUTPUT_DIR / "run_precheck_then_ebay.log"

# RocketSource endpoints to try (ordered)
ENDPOINTS = [
    "https://app.rocketsource.io/api/v3/scans/upload",   # app v3 direct upload endpoint (preferred)
    "https://app.rocketsource.io/api/v3/scans",          # /scans v3
    "https://app.rocketsource.io/api/v1/scans",          # older v1 (some return 405)
    "https://api.rocketsource.ai/v1/map",                # older map endpoints (may be unreachable)
]

# Minimal form fields RocketSource expects:
# "file" => file upload (json or csv); marketplace param and mapping param are common
# mapping format can vary by provider; we'll supply a conservative mapping object as JSON string.
DEFAULT_MAPPING = json.dumps([{"type": "gtin_or_mpn", "field": "gtin_mpn"}])  # placeholder mapping

# ------- Setup logging -------
os.makedirs(OUTPUT_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

# ------- Load env -------
if ENV_FILE.exists():
    load_dotenv(str(ENV_FILE))
    logging.info(f"Loaded env from {ENV_FILE}")
else:
    logging.warning(f".env file not found at {ENV_FILE}; continuing (will rely on env variables).")

ROCKET_KEY = os.getenv("rocket_sauce_API_KEY") or os.getenv("rocket_key") or os.getenv("sauce_api")
if not ROCKET_KEY:
    logging.error("RocketSource API key not found in environment (rocket_sauce_API_KEY). Aborting precheck.")
    sys.exit(1)

# ------- Helpers -------
def dns_ok(hostname: str) -> bool:
    try:
        socket.gethostbyname(hostname)
        return True
    except Exception as e:
        logging.debug(f"DNS check failed for {hostname}: {e}")
        return False

def load_identifiers_sample(path: Path, max_items=200):
    if not path.exists():
        logging.warning(f"Identifiers file not found at {path}. Precheck will use an empty sample (only test connectivity).")
        return []
    try:
        data = json.loads(path.read_text())
        # the identifiers file structure in your project is list of dicts; ensure minimal fields present
        sample = []
        for d in data[:max_items]:
            # ensure at least one id-like field present in the sample entry
            entry = {}
            entry["item_id"] = d.get("item_id") or d.get("itemId") or d.get("id")
            # keep variety of identifier fields if present
            for f in ("gtin", "upc", "ean", "mpn"):
                if d.get(f):
                    entry[f] = d.get(f)
            sample.append(entry)
        return sample
    except Exception as e:
        logging.exception("Failed to read identifiers file")
        return []

def do_multipart_upload_test(endpoint: str, sample_identifiers: list) -> Tuple[int, str, dict]:
    """
    Try to POST a multipart form upload.
    Returns: (status_code_or_-1, text_snippet, response_json_or_empty)
    """
    host = requests.utils.urlparse(endpoint).hostname or ""
    logging.info(f"Trying endpoint: {endpoint} (DNS OK?) {dns_ok(host)}")
    # Build a tiny JSON file to upload (or a CSV fallback)
    mapped_payload = {
        "marketplace": "amazon",
        # The API often requires 'mapping' or other meta fields — include a mapping to be safe.
        "mapping": DEFAULT_MAPPING
    }

    # prepare file in tmp
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tf:
        json.dump(sample_identifiers or [{"note":"empty-sample"}], tf)
        tf.flush()
        tmp_name = tf.name

    files = {
        # common RocketSource file field names tried in order by other tests:
        # we'll post as 'file' first (common), but caller may emulate other field names if needed.
        "file": (Path(tmp_name).name, open(tmp_name, "rb"), "application/json")
    }
    data = {
        "marketplace": "amazon",
        "mapping": DEFAULT_MAPPING
    }
    headers = {
        "Authorization": f"Bearer {ROCKET_KEY}"
    }

    try:
        resp = requests.post(endpoint, headers=headers, files=files, data=data, timeout=90)
        # close & cleanup
        files["file"][1].close()
        os.unlink(tmp_name)
        snippet = (resp.text[:1000] + "...") if len(resp.text) > 1000 else resp.text
        try:
            j = resp.json()
        except Exception:
            j = {}
        logging.info(f"→ POST multipart (file_field='file') Status: {resp.status_code}")
        return resp.status_code, snippet, j
    except Exception as e:
        # cleanup file handle if still open
        try:
            files["file"][1].close()
        except Exception:
            pass
        try:
            os.unlink(tmp_name)
        except Exception:
            pass
        logging.exception(f"Exception during multipart upload to {endpoint}: {e}")
        return -1, str(e), {}

# ------- Main precheck flow -------
def run_precheck_and_maybe_launch():
    logging.info("RocketSource multipart precheck starting...")
    sample = load_identifiers_sample(IDENTIFIERS_FILE, max_items=200)
    attempts = []
    success = False
    success_info = {}

    # Try endpoints in order; for each endpoint, try common file field names / content types implicitly
    for endpoint in ENDPOINTS:
        status, snippet, j = do_multipart_upload_test(endpoint, sample)
        attempts.append({
            "endpoint": endpoint,
            "status": status,
            "snippet": snippet,
            "json": j
        })

        # Treat 2xx as success; 202 Accepted is also OK
        if status and 200 <= status < 300:
            success = True
            success_info = attempts[-1]
            logging.info(f"Precheck success at {endpoint} (status {status})")
            break

        # If server returns 402 indicating billing/plan, bail but record
        if status == 402:
            logging.warning("Received 402 (billing/plan). Precheck failed due to plan restrictions.")
            break

        # 405 or 415 indicate server expects different method/structure — record and continue trying other endpoints
        # name resolution errors are status == -1 in our return value

    # Save detailed attempts JSON
    try:
        with open(RESULT_FILE, "w") as rf:
            json.dump({
                "ts": datetime.utcnow().isoformat(),
                "attempts": attempts,
                "success": success,
                "success_info": success_info
            }, rf, indent=2)
        logging.info(f"Saved precheck result -> {RESULT_FILE}")
    except Exception:
        logging.exception("Failed to write precheck results file")

    if not success:
        # Explain why we are stopping
        logging.error("Precheck did NOT succeed. See the saved result file for details.")
        # If we got a 402 specifically, mention it
        if any(a["status"] == 402 for a in attempts):
            logging.error("At least one endpoint returned 402: billing/plan issue (upgrade may be required).")
        if any(a["status"] == -1 for a in attempts):
            logging.error("At least one endpoint had DNS/connection errors (couldn't resolve host).")
        return False

    # If success -> launch ebay_scraping_recent.py in same environment
    # Launch using python found on PATH or sys.executable
    ebay_script = BASE_DIR / "Flipper" / "Flipper" / "ebay_scraping_recent.py"
    if not ebay_script.exists():
        # fallback to your other script names (older projects used ebay_scraper_with_rocket_sauce.py)
        fallback = BASE_DIR / "Flipper" / "Flipper" / "ebay_scraper_with_rocket_sauce.py"
        if fallback.exists():
            ebay_script = fallback

    if not ebay_script.exists():
        logging.error(f"Could not find ebay scraping script at {ebay_script}. Aborting launch.")
        return False

    logging.info(f"Launching ebay scraping script: {ebay_script}")
    # We run it as a subprocess so logs are visible in separate process; environment will carry .env values
    try:
        # Use sys.executable so the same Python and venv is used
        subprocess_env = os.environ.copy()
        proc = __import__("subprocess").Popen([sys.executable, str(ebay_script)], env=subprocess_env)
        logging.info(f"Spawned ebay scraper subprocess pid={proc.pid}")
        return True
    except Exception as e:
        logging.exception(f"Failed to launch ebay scraping script: {e}")
        return False

if __name__ == "__main__":
    ok = run_precheck_and_maybe_launch()
    if ok:
        logging.info("Precheck passed and ebay scraper launched.")
        sys.exit(0)
    else:
        logging.error("Precheck failed — not launching scraper.")
        sys.exit(2)
