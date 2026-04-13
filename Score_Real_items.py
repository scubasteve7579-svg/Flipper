import json
import os
from collections import defaultdict
from datetime import datetime

from dts_model import (
    DTS_THRESHOLD,
    compute_directional_summary,
    compute_fingerprint_fast_sell_through,
    predict_dts,
    train_dts_model,
)

# Default assumed profit margin when no trend data is available
DEFAULT_PROFIT_MARGIN = 0.3

# Paths
SOLD_ITEMS_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_recent/sold_items.json"
ACTIVE_ITEMS_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_recent/items.json"
KEEPA_SOLD_DATA = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/keepa_sold_data.json"
OUTPUT_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_recent/scored_combined_items.json"

# Minimum sold items required to train the ML model (otherwise fall back to heuristics)
MIN_TRAINING_SAMPLES = 20

# ---------------------------------------------------------------------------
# Feature builder — turns an item dict into numeric features for the model
# ---------------------------------------------------------------------------

def build_features(item):
    """Extract numeric features from an item for the DTS model."""
    try:
        price = float(item.get("price") or item.get("sold_price") or 0)
    except (TypeError, ValueError):
        price = 0.0
    category = (item.get("categoryPath") or item.get("category") or "").lower()
    condition = (item.get("condition") or "").lower()

    return {
        "price": price,
        "is_electronics": float("electronics" in category or "laptops" in category or "computers" in category),
        "is_new": float(condition in ("new", "brand new")),
        "is_used": float("used" in condition or "pre-owned" in condition),
        "has_free_shipping": float((item.get("shippingType") or "").lower() == "free"),
        "title_length": float(len(item.get("title") or "")),
    }


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Try ML model first — falls back to heuristics if not enough data
# ---------------------------------------------------------------------------
model = None
fingerprint_stats = None

# Filter to items that actually sold and have a duration
trainable = [
    item for item in all_sold
    if (item.get("sold") or ("sold_price" in item and item.get("sold_price")))
    and (item.get("duration") or item.get("days_to_sell") or item.get("dts"))
]

if len(trainable) >= MIN_TRAINING_SAMPLES:
    try:
        model, eval_results, fingerprint_stats = train_dts_model(
            trainable, build_features
        )
        # Print directional accuracy from the last training iteration
        if "train" in eval_results and "directional_accuracy" in eval_results["train"]:
            da = eval_results["train"]["directional_accuracy"][-1]
            bda_list = eval_results["train"].get("boundary_dir_acc", [])
            bda = bda_list[-1] if bda_list else None
            bda_str = f"{bda:.4f}" if bda is not None else "N/A"
            print(f"📊 Model trained — directional accuracy: {da:.4f}, "
                  f"boundary accuracy: {bda_str}")
        # Show fingerprint fast_sell_through summary
        if fingerprint_stats:
            print(f"🔑 Tracked {len(fingerprint_stats)} fingerprints for "
                  f"fast_sell_through rates")
    except Exception as exc:
        print(f"⚠️  ML training failed ({exc}), using heuristic fallback")
        model = None
else:
    print(f"ℹ️  Only {len(trainable)} trainable sold items "
          f"(need {MIN_TRAINING_SAMPLES}) — using heuristic scoring")


# ---------------------------------------------------------------------------
# Score active items
# ---------------------------------------------------------------------------
scored_active = []

if model is not None:
    # ---- ML-based scoring ---------------------------------------------
    scored_active = predict_dts(model, active_items, build_features,
                                fingerprint_stats=fingerprint_stats)
    for item in scored_active:
        dts = item.get("predicted_dts")
        fp_fast = item.get("fingerprint_fast_sell_through")

        # Confidence: blend model's fast/slow with fingerprint signal
        confidence = 0.5
        if item.get("fast_slow") == "fast":
            confidence += 0.2
        if fp_fast is not None and fp_fast > 0.6:
            confidence += 0.1

        category = (item.get("categoryPath") or "").lower()
        if "electronics" in category or "laptops" in category:
            confidence = min(0.9, confidence + 0.1)

        estimated_profit = float(item.get("price", 0)) * DEFAULT_PROFIT_MARGIN
        score = estimated_profit * confidence
        item["confidence"] = confidence
        item["score"] = score
        item["flip_potential"] = "high" if score > 100 else "medium" if score > 50 else "low"
        item["predicted_duration"] = (f"{int(round(dts))} days"
                                       if dts is not None else "7 days")
else:
    # ---- Heuristic fallback (original logic) --------------------------
    category_trends = defaultdict(lambda: {
        "total_profit": 0, "count": 0, "avg_profit": 0,
        "sales_volume": 0, "avg_duration": 0,
    })
    for item in all_sold:
        if item.get("sold") or ("sold_price" in item and item.get("sold_price")):
            category = item.get("categoryPath", "").lower()
            profit = (float(item.get("sold_price", 0))
                      - float(item.get("price", 0))) if "price" in item else 0
            duration = (int(item.get("duration", "1 day").split()[0])
                        if item.get("duration") else 1)
            count = 1
            if "keepa_sold_data" in item.get("url", ""):
                count = sum(1 for entry in keepa_items
                            if entry["item_id"] == item["item_id"])
            category_trends[category]["total_profit"] += profit
            category_trends[category]["count"] += count
            category_trends[category]["sales_volume"] += count
            category_trends[category]["avg_duration"] += duration

    for cat, data in category_trends.items():
        if data["count"] > 0:
            data["avg_profit"] = data["total_profit"] / data["count"]
            data["avg_duration"] = data["avg_duration"] / data["count"]

    # Compute fingerprint stats even in heuristic mode
    fingerprint_stats = compute_fingerprint_fast_sell_through(all_sold)

    for item in active_items:
        category = item.get("categoryPath", "").lower()
        trend = category_trends.get(category, {
            "total_profit": 0, "count": 0, "avg_profit": 0,
            "sales_volume": 0, "avg_duration": 0,
        })
        estimated_profit = trend["avg_profit"] or (float(item.get("price", 0)) * DEFAULT_PROFIT_MARGIN)

        confidence = 0.5
        if trend["sales_volume"] > 5:
            confidence += 0.2
        if trend["avg_duration"] < DTS_THRESHOLD:
            confidence += 0.1
        if "electronics" in category or "laptops" in category:
            confidence = min(0.9, confidence + 0.1)

        score = estimated_profit * confidence
        item["profit"] = estimated_profit
        item["confidence"] = confidence
        item["score"] = score
        item["flip_potential"] = ("high" if score > 100
                                  else "medium" if score > 50 else "low")
        item["predicted_duration"] = (f"{int(trend['avg_duration'])} days"
                                       if trend["count"] > 0 else "7 days")
        item["fast_slow"] = ("fast" if trend["avg_duration"] < DTS_THRESHOLD
                             else "slow")
        scored_active.append(item)


# ---------------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------------
combined_scored = all_sold + scored_active
with open(OUTPUT_FILE, 'w') as f:
    json.dump(combined_scored, f, indent=2)

mode = "ML model" if model is not None else "heuristic"
print(f"✅ Scored {len(scored_active)} active items ({mode}) using "
      f"{len(all_sold)} sold items. Saved to {OUTPUT_FILE}.")