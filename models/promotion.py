def PromotionModel(
    target_sku: str = "ZINGER_BURGER",
    discount_pct: float = 0.20,
    target_stores: int = 16,
    target_segment: str = "all",
    attach_rate_assumption: float = 0.35,
    base_daily_txns_per_store: float = 30,
    avg_sku_price_pkr: float = 450,
    avg_basket_pkr: float = 850,
    food_cost_ratio: float = 0.28,
    transaction_lift_elasticity: float = 1.5,
):
    """
    Estimate net P&L impact of a SKU discount promotion.
    attach_rate_assumption: fraction of lifted transactions that add a side/drink
    transaction_lift_elasticity: transaction lift multiplier = discount_pct * elasticity
    """
    transaction_lift_pct = discount_pct * transaction_lift_elasticity
    base_daily_txns = base_daily_txns_per_store * target_stores

    lifted_txns  = base_daily_txns * transaction_lift_pct
    total_txns   = base_daily_txns + lifted_txns

    discounted_price = avg_sku_price_pkr * (1 - discount_pct)
    discount_abs     = avg_sku_price_pkr * discount_pct

    cogs_per_unit    = avg_sku_price_pkr * food_cost_ratio
    margin_original  = avg_sku_price_pkr - cogs_per_unit
    margin_discounted= discounted_price  - cogs_per_unit

    attach_revenue   = lifted_txns * attach_rate_assumption * (avg_basket_pkr - avg_sku_price_pkr) * 0.30

    revenue_change = (
        lifted_txns * discounted_price
        - base_daily_txns * discount_abs
        + attach_revenue
    )
    cogs_change   = lifted_txns * cogs_per_unit
    net_pkr_impact = revenue_change - cogs_change
    basket_value_change = (
        (total_txns * avg_basket_pkr * (1 - discount_pct * (avg_sku_price_pkr / avg_basket_pkr))
         - base_daily_txns * avg_basket_pkr)
        / base_daily_txns
    )

    return {
        "parameters": {
            "target_sku":               target_sku,
            "discount_pct":             discount_pct,
            "target_stores":            target_stores,
            "target_segment":           target_segment,
            "attach_rate_assumption":   attach_rate_assumption,
            "base_daily_txns_per_store":base_daily_txns_per_store,
            "avg_sku_price_pkr":        avg_sku_price_pkr,
            "avg_basket_pkr":           avg_basket_pkr,
            "food_cost_ratio":          food_cost_ratio,
            "transaction_lift_elasticity": transaction_lift_elasticity,
        },
        "outputs": {
            "transaction_lift_pct":       round(transaction_lift_pct * 100, 1),
            "lifted_transactions_per_day":round(lifted_txns,  1),
            "total_transactions_per_day": round(total_txns,   1),
            "discounted_sku_price_pkr":   round(discounted_price, 2),
            "margin_at_discount_pkr":     round(margin_discounted, 2),
            "margin_original_pkr":        round(margin_original,   2),
            "attach_revenue_per_day_pkr": round(attach_revenue,    2),
            "basket_value_change_pkr":    round(basket_value_change,2),
            "net_pkr_impact_per_day":     round(net_pkr_impact,    2),
            "annualised_pkr":             round(net_pkr_impact * 365, 2),
            "margin_change_pct":          round(
                (margin_discounted - margin_original) / margin_original * 100
                if margin_original else 0, 1
            ),
        },
    }
