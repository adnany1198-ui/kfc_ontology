DEFAULT_FOOD_COST_RATIOS = {
    "BEVERAGE":       0.15,
    "SOFT SERVE":     0.18,
    "ADD ON":         0.20,
    "SNACKS":         0.25,
    "ALA CARTE":      0.28,
    "EDV":            0.28,
    "MEAL BOX":       0.30,
    "MAKE IT A MEAL": 0.30,
    "SHARING":        0.32,
}


def MarginModel(
    basket_value: float = 850.0,
    category_mix: dict = None,
    food_cost_ratios: dict = None,
):
    """
    Compute gross margin given basket value and category mix.
    category_mix: {category_name: fraction_of_basket} (must sum to ~1.0)
    food_cost_ratios: override defaults per category
    """
    if category_mix is None:
        category_mix = {"ALA CARTE": 0.40, "MEAL BOX": 0.30, "SHARING": 0.20, "BEVERAGE": 0.10}

    ratios = {**DEFAULT_FOOD_COST_RATIOS}
    if food_cost_ratios:
        ratios.update({k.upper(): v for k, v in food_cost_ratios.items()})

    total_pct = sum(category_mix.values())
    if abs(total_pct - 1.0) > 0.05:
        category_mix = {k: v / total_pct for k, v in category_mix.items()}

    margin_by_category = {}
    blended_cost_ratio = 0.0
    for cat, frac in category_mix.items():
        cat_upper = cat.upper()
        cost_ratio = ratios.get(cat_upper, 0.28)
        cat_revenue   = basket_value * frac
        cat_cogs      = cat_revenue  * cost_ratio
        cat_margin    = cat_revenue  - cat_cogs
        blended_cost_ratio += frac * cost_ratio
        margin_by_category[cat] = {
            "revenue_pkr":   round(cat_revenue, 2),
            "cogs_pkr":      round(cat_cogs,    2),
            "margin_pkr":    round(cat_margin,  2),
            "margin_pct":    round((1 - cost_ratio) * 100, 1),
            "food_cost_ratio": cost_ratio,
        }

    total_cogs   = basket_value * blended_cost_ratio
    gross_margin = basket_value - total_cogs

    return {
        "parameters": {
            "basket_value":     basket_value,
            "category_mix":     category_mix,
            "food_cost_ratios": {k: ratios.get(k.upper(), 0.28) for k in category_mix},
        },
        "outputs": {
            "gross_margin_pkr":      round(gross_margin,         2),
            "gross_margin_pct":      round((1 - blended_cost_ratio) * 100, 1),
            "total_cogs_pkr":        round(total_cogs,            2),
            "blended_food_cost_ratio": round(blended_cost_ratio,  3),
            "margin_by_category":    margin_by_category,
        },
    }
