DEFAULT_SKU_DEPENDENCIES = {
    "ZINGER_BURGER":  {"POULTRY_BST": 0.65, "FLOUR_RFD": 0.10, "COOK_OIL": 0.12},
    "CHICKEN_PC":     {"POULTRY_WHL": 0.70, "COOK_OIL":  0.15, "FLOUR_RFD": 0.05},
    "TWISTER":        {"POULTRY_BST": 0.55, "FLOUR_RFD": 0.12, "COOK_OIL": 0.10},
    "RICE_BOWL":      {"POULTRY_WHL": 0.45, "RICE_BSM":  0.30, "COOK_OIL": 0.05},
    "KRUNCH_BURGER":  {"POULTRY_WHL": 0.60, "FLOUR_RFD": 0.10, "COOK_OIL": 0.12},
    "FRIES_REG":      {"COOK_OIL":    0.35, "FLOUR_RFD": 0.05},
    "SOFT_DRINK":     {"BEV_CONC":    0.55},
    "SOFT_SERVE":     {"BEV_CONC":    0.20, "COOK_OIL":  0.05},
}


def DemandShockModel(
    commodity: str = "POULTRY_WHL",
    pct_change: float = 0.32,
    sku_dependency_weights: dict = None,
):
    """
    Compute SKU-level COGS impact of a commodity price shock.
    pct_change: fractional change (0.32 = +32%)
    sku_dependency_weights: {sku: {commodity: weight_in_cogs}} — defaults used if None
    """
    if sku_dependency_weights is None:
        sku_dependency_weights = DEFAULT_SKU_DEPENDENCIES

    commodity_upper = commodity.upper()
    sku_impacts = {}
    affected_skus = []

    for sku, deps in sku_dependency_weights.items():
        dep_upper = {k.upper(): v for k, v in deps.items()}
        if commodity_upper not in dep_upper:
            continue
        weight = dep_upper[commodity_upper]
        cogs_change_pct = weight * pct_change
        sku_impacts[sku] = {
            "commodity_weight_in_cogs": round(weight, 3),
            "cogs_change_pct":          round(cogs_change_pct * 100, 2),
            "margin_compression_pct":   round(cogs_change_pct * 100, 2),
        }
        affected_skus.append(sku)

    if not sku_impacts:
        avg_impact = 0.0
        blended_compression = 0.0
    else:
        avg_impact          = sum(v["cogs_change_pct"] for v in sku_impacts.values()) / len(sku_impacts)
        blended_compression = sum(v["margin_compression_pct"] for v in sku_impacts.values()) / len(sku_impacts)

    all_stores = list(range(16))

    return {
        "parameters": {
            "commodity":              commodity,
            "pct_change":             pct_change,
            "sku_dependency_weights": sku_dependency_weights,
        },
        "outputs": {
            "affected_skus":             affected_skus,
            "n_affected_skus":           len(affected_skus),
            "sku_cogs_impacts":          sku_impacts,
            "avg_cogs_change_pct":       round(avg_impact,          2),
            "avg_margin_compression_pct":round(blended_compression, 2),
            "affected_stores":           "all — commodity-wide shock",
        },
    }
