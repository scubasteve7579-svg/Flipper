"""
DTS (Days-to-Sell) prediction model with directional accuracy optimization.

Addresses four gaps between MAE optimization and fast/slow directional accuracy:
  1. Threshold-aware custom objective — penalizes wrong-side-of-7 predictions harder
  2. Directional accuracy metrics — tracks fast (<7d) vs slow (>=7d) classification
  3. Boundary upweighting — items with DTS 4–14 get more gradient signal
  4. Fingerprint fast_sell_through — % of sold items per fingerprint with DTS < 7
"""

import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DTS_THRESHOLD = 7                       # days: fast (<7) vs slow (>=7)
LOG_THRESHOLD = math.log1p(DTS_THRESHOLD)  # ≈ 2.079 in log1p space
BOUNDARY_LOW = 4                        # lower edge of decision boundary zone
BOUNDARY_HIGH = 14                      # upper edge of decision boundary zone
WRONG_SIDE_PENALTY = 2.0                # extra penalty multiplier for cross-boundary errors
BOUNDARY_WEIGHT_BOOST = 3.0             # extra sample weight for items in boundary zone
FRESHNESS_HALFLIFE_DAYS = 30            # half-life for recency weighting


# ---------------------------------------------------------------------------
# 1. Threshold-aware custom objective for LightGBM
# ---------------------------------------------------------------------------

def directional_mae_objective(y_pred, dtrain):
    """Custom LightGBM objective: MAE in log1p space with extra penalty for
    predictions that land on the wrong side of LOG_THRESHOLD.

    Parameters
    ----------
    y_pred : np.ndarray   – current predictions (log1p scale)
    dtrain : lgb.Dataset  – training dataset (label = log1p(DTS))

    Returns
    -------
    grad : np.ndarray  – first-order gradients
    hess : np.ndarray  – second-order "gradients" (kept > 0 for stability)
    """
    y_true = dtrain.get_label()
    residual = y_pred - y_true  # positive = over-predicted

    # Base MAE gradient: sign(residual)
    grad = np.sign(residual)
    hess = np.ones_like(residual)  # constant curvature for L1

    # Identify wrong-side predictions
    true_fast = y_true < LOG_THRESHOLD
    pred_fast = y_pred < LOG_THRESHOLD
    wrong_side = true_fast != pred_fast  # predicted fast when true slow, or vice-versa

    # Apply extra penalty multiplier on wrong-side predictions
    grad[wrong_side] *= WRONG_SIDE_PENALTY
    hess[wrong_side] *= WRONG_SIDE_PENALTY

    return grad, hess


# ---------------------------------------------------------------------------
# 2. Directional accuracy evaluation metric for LightGBM
# ---------------------------------------------------------------------------

def directional_accuracy_metric(y_pred, dtrain):
    """LightGBM evaluation metric: % of predictions on the correct side of 7 days.

    Returns (name, value, is_higher_better).
    """
    y_true = dtrain.get_label()
    true_fast = y_true < LOG_THRESHOLD
    pred_fast = y_pred < LOG_THRESHOLD
    accuracy = np.mean(true_fast == pred_fast)
    return "directional_accuracy", accuracy, True


def boundary_directional_accuracy_metric(y_pred, dtrain):
    """Directional accuracy restricted to the DTS 4–14 boundary zone.

    This is the metric that matters most — items right around the decision line.
    """
    y_true = dtrain.get_label()
    log_low = math.log1p(BOUNDARY_LOW)
    log_high = math.log1p(BOUNDARY_HIGH)
    mask = (y_true >= log_low) & (y_true <= log_high)
    if mask.sum() == 0:
        return "boundary_dir_acc", 0.0, True
    true_fast = y_true[mask] < LOG_THRESHOLD
    pred_fast = y_pred[mask] < LOG_THRESHOLD
    accuracy = np.mean(true_fast == pred_fast)
    return "boundary_dir_acc", accuracy, True


# ---------------------------------------------------------------------------
# 3. Boundary upweighting — sample weights for training
# ---------------------------------------------------------------------------

def compute_sample_weights(dts_values, sold_dates=None, reference_date=None):
    """Compute per-sample weights that upweight the decision boundary zone
    and optionally incorporate freshness decay.

    Parameters
    ----------
    dts_values : array-like of float – raw DTS in days (not log-transformed)
    sold_dates : list[str | datetime] | None – ISO-format sold dates for
        freshness weighting.  Pass ``None`` to skip freshness.
    reference_date : datetime | None – "now" for freshness calc; defaults to
        UTC now.

    Returns
    -------
    weights : np.ndarray of float
    """
    dts = np.asarray(dts_values, dtype=float)
    weights = np.ones(len(dts))

    # Upweight the 4–14 day boundary zone
    boundary_mask = (dts >= BOUNDARY_LOW) & (dts <= BOUNDARY_HIGH)
    weights[boundary_mask] *= BOUNDARY_WEIGHT_BOOST

    # Freshness weighting (exponential decay by sold date)
    if sold_dates is not None:
        if reference_date is None:
            reference_date = datetime.now(timezone.utc)
        elif reference_date.tzinfo is None:
            reference_date = reference_date.replace(tzinfo=timezone.utc)
        for i, d in enumerate(sold_dates):
            if d is None:
                continue
            if isinstance(d, str):
                d = datetime.fromisoformat(d.replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            age_days = (reference_date - d).total_seconds() / 86400
            freshness = math.pow(0.5, age_days / FRESHNESS_HALFLIFE_DAYS)
            weights[i] *= freshness

    return weights


# ---------------------------------------------------------------------------
# 4. Fingerprint fast_sell_through tracking
# ---------------------------------------------------------------------------

def compute_fingerprint_fast_sell_through(items, fingerprint_fn=None):
    """For each unique fingerprint, compute the fraction of sold items with
    DTS < 7 (fast sell-through rate).

    Parameters
    ----------
    items : list[dict] – sold item records.  Each must have at least a
        "duration" (or "days_to_sell") field.  If ``fingerprint_fn`` is not
        given, the fingerprint defaults to (category, condition, price_bucket).
    fingerprint_fn : callable | None – ``fn(item) -> str`` returning a
        fingerprint key.

    Returns
    -------
    dict[str, dict]  – mapping fingerprint → {
        "total": int,
        "fast_count": int,
        "fast_sell_through": float (0-1),
    }
    """
    if fingerprint_fn is None:
        fingerprint_fn = _default_fingerprint

    stats = defaultdict(lambda: {"total": 0, "fast_count": 0})

    for item in items:
        dts = _extract_dts(item)
        if dts is None:
            continue
        fp = fingerprint_fn(item)
        stats[fp]["total"] += 1
        if dts < DTS_THRESHOLD:
            stats[fp]["fast_count"] += 1

    result = {}
    for fp, s in stats.items():
        rate = s["fast_count"] / s["total"] if s["total"] > 0 else 0.0
        result[fp] = {
            "total": s["total"],
            "fast_count": s["fast_count"],
            "fast_sell_through": round(rate, 4),
        }

    return result


# ---------------------------------------------------------------------------
# 5. Full training helper
# ---------------------------------------------------------------------------

def train_dts_model(sold_items, feature_builder, lgb_params=None):
    """Train a LightGBM model on sold items with all four improvements.

    Parameters
    ----------
    sold_items : list[dict] – sold item records with at least duration and
        a sold date.
    feature_builder : callable – ``fn(item) -> dict[str, float]`` returning
        numeric features for one item.
    lgb_params : dict | None – overrides for LightGBM parameters.

    Returns
    -------
    model : lgb.Booster
    eval_results : dict – directional accuracy and other metrics logged
        during training.
    fingerprint_stats : dict – fast_sell_through per fingerprint.
    """
    import lightgbm as lgb

    # ---- Extract targets + features ----------------------------------
    rows = []
    dts_raw = []
    sold_dates = []
    for item in sold_items:
        dts = _extract_dts(item)
        if dts is None:
            continue
        feats = feature_builder(item)
        if feats is None:
            continue
        rows.append(feats)
        dts_raw.append(dts)
        sold_dates.append(item.get("sold_date") or item.get("endTime"))

    if not rows:
        raise ValueError("No valid training samples found.")

    feature_names = sorted(rows[0].keys())
    X = np.array([[r[f] for f in feature_names] for r in rows], dtype=np.float64)
    y = np.log1p(np.array(dts_raw, dtype=np.float64))

    # ---- Sample weights ----------------------------------------------
    weights = compute_sample_weights(dts_raw, sold_dates=sold_dates)

    # ---- Build LightGBM datasets -------------------------------------
    dtrain = lgb.Dataset(X, label=y, weight=weights, feature_name=feature_names)

    # ---- Parameters ---------------------------------------------------
    params = {
        "objective": directional_mae_objective,
        "verbose": -1,
        "num_leaves": 31,
        "learning_rate": 0.05,
        "min_child_samples": 10,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "metric": "None",  # disable default metric; using custom feval
    }
    if lgb_params:
        params.update(lgb_params)

    # ---- Train --------------------------------------------------------
    eval_results = {}
    model = lgb.train(
        params,
        dtrain,
        num_boost_round=500,
        feval=[directional_accuracy_metric, boundary_directional_accuracy_metric],
        valid_sets=[dtrain],
        valid_names=["train"],
        callbacks=[
            lgb.record_evaluation(eval_results),
            lgb.log_evaluation(period=50),
        ],
    )

    # ---- Fingerprint stats -------------------------------------------
    fingerprint_stats = compute_fingerprint_fast_sell_through(sold_items)

    return model, eval_results, fingerprint_stats


# ---------------------------------------------------------------------------
# 6. Prediction helper
# ---------------------------------------------------------------------------

def predict_dts(model, items, feature_builder, fingerprint_stats=None):
    """Score items and attach fast/slow classification + fingerprint signal.

    Parameters
    ----------
    model : lgb.Booster
    items : list[dict]
    feature_builder : callable
    fingerprint_stats : dict | None – from ``compute_fingerprint_fast_sell_through``

    Returns
    -------
    list[dict] – input items enriched with prediction fields.
    """
    feature_names = model.feature_name()
    for item in items:
        feats = feature_builder(item)
        if feats is None:
            item["predicted_dts"] = None
            item["fast_slow"] = "unknown"
            continue

        x = np.array([[feats.get(f, 0.0) for f in feature_names]])
        log_pred = model.predict(x)[0]
        dts_pred = math.expm1(log_pred)

        item["predicted_dts"] = round(max(dts_pred, 0.0), 2)
        item["fast_slow"] = "fast" if dts_pred < DTS_THRESHOLD else "slow"
        item["log1p_pred"] = round(log_pred, 4)

        # Attach fingerprint signal
        if fingerprint_stats is not None:
            fp = _default_fingerprint(item)
            fp_info = fingerprint_stats.get(fp)
            if fp_info:
                item["fingerprint"] = fp
                item["fingerprint_fast_sell_through"] = fp_info["fast_sell_through"]
                item["fingerprint_volume"] = fp_info["total"]

    return items


# ---------------------------------------------------------------------------
# Evaluation summary
# ---------------------------------------------------------------------------

def compute_directional_summary(y_true_dts, y_pred_dts):
    """Return a human-readable summary of directional accuracy metrics.

    Parameters
    ----------
    y_true_dts : array-like – actual DTS in days
    y_pred_dts : array-like – predicted DTS in days

    Returns
    -------
    dict with overall_dir_acc, boundary_dir_acc, fast_precision, fast_recall,
    slow_precision, slow_recall, mae, and counts.
    """
    yt = np.asarray(y_true_dts, dtype=float)
    yp = np.asarray(y_pred_dts, dtype=float)

    true_fast = yt < DTS_THRESHOLD
    pred_fast = yp < DTS_THRESHOLD
    correct = true_fast == pred_fast

    # Overall
    overall_acc = np.mean(correct) if len(correct) > 0 else 0.0

    # Boundary zone (4–14)
    bnd = (yt >= BOUNDARY_LOW) & (yt <= BOUNDARY_HIGH)
    bnd_acc = np.mean(correct[bnd]) if bnd.sum() > 0 else 0.0

    # Precision / recall for fast class
    tp_fast = (pred_fast & true_fast).sum()
    fp_fast = (pred_fast & ~true_fast).sum()
    fn_fast = (~pred_fast & true_fast).sum()
    fast_prec = tp_fast / (tp_fast + fp_fast) if (tp_fast + fp_fast) > 0 else 0.0
    fast_rec = tp_fast / (tp_fast + fn_fast) if (tp_fast + fn_fast) > 0 else 0.0

    # Precision / recall for slow class
    tp_slow = (~pred_fast & ~true_fast).sum()
    fp_slow = (~pred_fast & true_fast).sum()
    fn_slow = (pred_fast & ~true_fast).sum()
    slow_prec = tp_slow / (tp_slow + fp_slow) if (tp_slow + fp_slow) > 0 else 0.0
    slow_rec = tp_slow / (tp_slow + fn_slow) if (tp_slow + fn_slow) > 0 else 0.0

    return {
        "overall_directional_accuracy": round(float(overall_acc), 4),
        "boundary_directional_accuracy": round(float(bnd_acc), 4),
        "fast_precision": round(float(fast_prec), 4),
        "fast_recall": round(float(fast_rec), 4),
        "slow_precision": round(float(slow_prec), 4),
        "slow_recall": round(float(slow_rec), 4),
        "mae_days": round(float(np.mean(np.abs(yt - yp))), 4),
        "total_samples": int(len(yt)),
        "boundary_samples": int(bnd.sum()),
        "true_fast_count": int(true_fast.sum()),
        "true_slow_count": int((~true_fast).sum()),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_dts(item):
    """Pull Days-to-Sell from an item dict, returning float or None."""
    # Prefer explicit numeric field
    for key in ("days_to_sell", "dts", "DTS"):
        if key in item and item[key] is not None:
            try:
                return float(item[key])
            except (ValueError, TypeError):
                pass
    # Fall back to "duration" string like "5 days"
    dur = item.get("duration")
    if dur and isinstance(dur, str):
        try:
            return float(dur.split()[0])
        except (ValueError, IndexError):
            pass
    return None


def _price_bucket(price):
    """Bucket a price into a coarse tier label."""
    try:
        p = float(price)
    except (TypeError, ValueError):
        return "unknown"
    if p < 25:
        return "0-25"
    if p < 75:
        return "25-75"
    if p < 200:
        return "75-200"
    if p < 500:
        return "200-500"
    return "500+"


def _default_fingerprint(item):
    """Produce a coarse fingerprint: (category, condition, price_bucket)."""
    cat = (item.get("categoryPath") or item.get("category") or "unknown").lower().strip()
    cond = (item.get("condition") or "unknown").lower().strip()
    price = item.get("price") or item.get("sold_price") or 0
    bucket = _price_bucket(price)
    return f"{cat}|{cond}|{bucket}"
