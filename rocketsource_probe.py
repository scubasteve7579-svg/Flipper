#!/usr/bin/env python3
"""
probe RockeSource upload endpoints/methods so we can see what they accept.
Save as rocketsource_probe.py and run with your venv Python.
"""

import requests, os, sys, time, json

ROCKET_KEY = "6110|hA5FSgCT60E9kIQcmp3BgA3kPC6KfnpWWimivhoS1503f800"
BASE = "https://app.rocketsource.io"
# endpoints to try (we tried /v1/map, /upload earlier; include a few plausible alternatives)
ENDPOINTS = [
    "/v1/map",
    "/v1/map/",    # sometimes trailing slash matters
    "/upload",
    "/upload/",
    "/api/upload",
    "/api/upload/",
    "/api/v3/scans",
    "/api/v3/scans/",
    "/api/v1/upload",
    "/api/v1/upload/"
]
METHODS = ["GET", "HEAD", "POST", "PUT"]
CSV_PATH = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/rocket_upload.csv"
JSON_PATH = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/rocket_upload.json"

LOG = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/rocket_probe.log"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def try_get(path):
    url = BASE + path
    headers = {"Authorization": f"Bearer {ROCKET_KEY}"}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        log(f"GET {path} → {r.status_code} | Allow: {r.headers.get('Allow')} | Content-Type: {r.headers.get('Content-Type')}")
        snippet = r.text[:800].replace("\n"," ")
        log(f"   snippet: {snippet}")
    except Exception as e:
        log(f"GET {path} exception: {e}")

def try_upload(path, method="PUT", use_csv=True):
    url = BASE + path
    headers = {"Authorization": f"Bearer {ROCKET_KEY}"}
    data = {"marketplace": "amazon", "mapping": "true"}  # or "mapping": "1" — check docs
    files = {}
    if use_csv and os.path.exists(CSV_PATH):
        files["file"] = ("rocket_upload.csv", open(CSV_PATH,"rb"), "text/csv")
    elif (not use_csv) and os.path.exists(JSON_PATH):
        files["file"] = ("rocket_upload.json", open(JSON_PATH,"rb"), "application/json")
    else:
        log(f"Upload skipped ({'csv' if use_csv else 'json'} missing): {CSV_PATH if use_csv else JSON_PATH}")
        return

    log(f"Attempting {method} {path} with {'CSV' if use_csv else 'JSON'} ({os.path.getsize(CSV_PATH) if use_csv else os.path.getsize(JSON_PATH)} bytes)")
    try:
        if method == "PUT":
            r = requests.put(url, headers=headers, data=data, files=files, timeout=60)
        else:
            r = requests.post(url, headers=headers, data=data, files=files, timeout=60)
        log(f"  → {r.status_code} | Allow: {r.headers.get('Allow')} | Content-Type: {r.headers.get('Content-Type')}")
        text = r.text[:2000].replace("\n"," ")
        log(f"  resp-snippet: {text}")
    except Exception as e:
        log(f"  exception: {e}")
    finally:
        # close file objects in files dict
        for f in list(files.values()):
            try:
                f[1].close()
            except Exception:
                pass

def main():
    log("=== rocketsource_probe starting ===")
    # quick GET/HEAD check
    for ep in ENDPOINTS:
        try_get(ep)
    # try upload combos
    for ep in ENDPOINTS:
        for method in ("PUT","POST"):
            try_upload(ep, method=method, use_csv=True)
            try_upload(ep, method=method, use_csv=False)
    log("=== rocketsource_probe finished ===")

if __name__ == "__main__":
    main()
