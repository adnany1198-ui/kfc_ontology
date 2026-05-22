"""
Generate synthetic Prism CV observations for ~70% of real transactions.
Anchored to real POS via transaction_id/store_id. Seed 42.
"""
import os
import hashlib
import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SEED     = 42
MATCH_RATE = 0.70

AGE_BANDS   = ["18-24", "25-34", "35-44", "45-54", "55+"]
GENDERS     = ["M", "F"]
CONF_TIERS  = ["HIGH", "MEDIUM", "LOW"]
ARCHETYPES  = ["urban_young", "family_suburban", "mixed"]


def store_archetype(store_id):
    h = int(hashlib.md5(str(store_id).encode()).hexdigest(), 16)
    return ARCHETYPES[h % 3]


def archetype_age_weights(archetype):
    if archetype == "urban_young":
        return [0.35, 0.30, 0.18, 0.10, 0.07]
    if archetype == "family_suburban":
        return [0.10, 0.25, 0.30, 0.22, 0.13]
    return [0.20, 0.28, 0.25, 0.17, 0.10]


def archetype_gender_weights(archetype):
    if archetype == "urban_young":
        return [0.62, 0.38]
    if archetype == "family_suburban":
        return [0.52, 0.48]
    return [0.58, 0.42]


def derive_group_size(channel, categories, item_count):
    if channel == "DRIVE THRU":
        base = [0.65, 0.25, 0.07, 0.03]
    elif any(c in ["SHARING", "MEAL BOX", "MAKE IT A MEAL"] for c in categories):
        base = [0.05, 0.20, 0.40, 0.35]
    elif item_count >= 5:
        base = [0.05, 0.15, 0.40, 0.40]
    elif any(c in ["EDV", "ALA CARTE"] for c in categories):
        base = [0.70, 0.20, 0.07, 0.03]
    else:
        base = [0.40, 0.35, 0.15, 0.10]
    return base


def derive_age_adjustment(hour, base_weights):
    weights = list(base_weights)
    if 11 <= hour <= 14:
        weights[0] += 0.08
        weights[1] += 0.05
        weights[3] -= 0.07
        weights[4] -= 0.06
    elif 18 <= hour <= 21:
        weights[2] += 0.08
        weights[3] += 0.05
        weights[0] -= 0.07
        weights[1] -= 0.06
    total = sum(weights)
    return [max(0.01, w / total) for w in weights]


def confidence_for_hour(hour):
    busy = (12 <= hour <= 14) or (19 <= hour <= 21)
    if busy:
        return [0.50, 0.35, 0.15]
    return [0.65, 0.28, 0.07]


def main():
    txn_path  = os.path.join(DATA_DIR, "pos_transactions.csv")
    item_path = os.path.join(DATA_DIR, "pos_line_items.csv")

    print("Loading POS data...")
    txns  = pd.read_csv(txn_path,  low_memory=False)
    items = pd.read_csv(item_path, low_memory=False)
    items["quantity"] = pd.to_numeric(items["quantity"], errors="coerce").fillna(1)
    txns["item_count"] = pd.to_numeric(txns["item_count"], errors="coerce").fillna(2)
    txns["timestamp"]  = pd.to_datetime(txns["timestamp"], errors="coerce", utc=True)
    txns["hour"]       = txns["timestamp"].dt.hour.fillna(12).astype(int)

    if "channel" not in txns.columns:
        txns["channel"] = "UNKNOWN"

    txn_categories = (
        items.groupby("transaction_id")["category"]
        .apply(list)
        .reset_index()
        .rename(columns={"category": "categories"})
    )
    txns = txns.merge(txn_categories, on="transaction_id", how="left")
    txns["categories"] = txns["categories"].apply(lambda x: x if isinstance(x, list) else [])

    rng = np.random.default_rng(SEED)
    mask = rng.random(len(txns)) < MATCH_RATE
    matched = txns[mask].copy().reset_index(drop=True)
    print(f"  {len(matched):,} transactions selected ({MATCH_RATE*100:.0f}% of {len(txns):,})")

    obs = []
    for i, row in matched.iterrows():
        if i % 10000 == 0:
            print(f"  Processing {i:,}/{len(matched):,}...", end="\r")

        archetype = store_archetype(row["store_id"])
        hour      = int(row["hour"]) if not pd.isna(row["hour"]) else 12
        channel   = row.get("channel", "UNKNOWN")
        cats      = row.get("categories", [])
        item_cnt  = int(row["item_count"]) if not pd.isna(row["item_count"]) else 2

        age_base  = archetype_age_weights(archetype)
        age_w     = derive_age_adjustment(hour, age_base)
        gen_w     = archetype_gender_weights(archetype)
        grp_w     = derive_group_size(channel, cats, item_cnt)
        conf_w    = confidence_for_hour(hour)

        age_band      = rng.choice(AGE_BANDS,   p=age_w)
        gender        = rng.choice(GENDERS,      p=gen_w)
        group_size    = rng.choice([1, 2, 3, 4], p=grp_w)
        dwell_seconds = int(rng.integers(5, 91))
        conf_tier     = rng.choice(CONF_TIERS,   p=conf_w)

        obs.append({
            "observation_id": f"PRS-{row['transaction_id']}",
            "transaction_id": row["transaction_id"],
            "store_id":       row["store_id"],
            "timestamp":      row["timestamp"],
            "age_band":       age_band,
            "gender":         gender,
            "group_size":     group_size,
            "dwell_seconds":  dwell_seconds,
            "confidence_tier":conf_tier,
            "store_archetype":archetype,
        })

    print(f"\n  Generated {len(obs):,} observations")
    out_path = os.path.join(DATA_DIR, "prism_observations.csv")
    pd.DataFrame(obs).to_csv(out_path, index=False)
    print(f"Saved: {out_path}")
    print("Done.")


if __name__ == "__main__":
    main()
