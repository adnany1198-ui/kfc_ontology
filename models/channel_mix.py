def ChannelMixModel(
    current_mix: dict = None,
    shift_from_channel: str = "DELIVERY",
    shift_to_channel: str = "EAT IN",
    shift_pct: float = 0.20,
    foodpanda_commission_pct: float = 0.30,
    own_delivery_cost_per_order: float = 150,
    loyalty_incentive_cost: float = 50,
    basket_value_change_pct: float = 0.05,
    daily_transactions: int = 500,
    avg_basket_pkr: float = 850,
):
    """
    Model per-transaction margin impact of shifting orders between channels.
    foodpanda_commission_pct: fraction of basket value paid to aggregator
    own_delivery_cost_per_order: fixed cost for own delivery fleet
    loyalty_incentive_cost: cost per shifted transaction (voucher, etc.)
    basket_value_change_pct: how basket changes in target channel vs source
    """
    if current_mix is None:
        current_mix = {
            "EAT IN":     0.40,
            "EAT OUT":    0.20,
            "DRIVE THRU": 0.15,
            "DELIVERY":   0.25,
        }

    total_pct = sum(current_mix.values())
    if abs(total_pct - 1.0) > 0.05:
        current_mix = {k: v / total_pct for k, v in current_mix.items()}

    shift_from_upper = shift_from_channel.upper()
    shift_to_upper   = shift_to_channel.upper()

    from_pct = current_mix.get(shift_from_upper, current_mix.get(shift_from_channel, 0))
    actual_shift = min(shift_pct, from_pct)

    new_mix = dict(current_mix)
    new_mix[shift_from_upper] = new_mix.get(shift_from_upper, from_pct) - actual_shift
    new_mix[shift_to_upper]   = new_mix.get(shift_to_upper, 0) + actual_shift

    def channel_margin_per_txn(channel, basket):
        ch = channel.upper()
        if ch == "DELIVERY" and shift_from_upper == "DELIVERY":
            return basket * (1 - foodpanda_commission_pct)
        elif ch == shift_to_upper and shift_to_upper not in ("EAT IN", "EAT OUT", "DRIVE THRU"):
            return basket - own_delivery_cost_per_order
        else:
            return basket

    old_revenue_per_txn = sum(
        pct * channel_margin_per_txn(ch, avg_basket_pkr)
        for ch, pct in current_mix.items()
    )
    shifted_basket = avg_basket_pkr * (1 + basket_value_change_pct)
    new_revenue_per_txn = (
        sum(
            pct * channel_margin_per_txn(ch, avg_basket_pkr)
            for ch, pct in new_mix.items()
            if ch != shift_to_upper
        )
        + new_mix.get(shift_to_upper, 0) * channel_margin_per_txn(shift_to_upper, shifted_basket)
        - actual_shift * loyalty_incentive_cost
    )

    per_txn_change = new_revenue_per_txn - old_revenue_per_txn
    daily_impact   = per_txn_change * daily_transactions
    annualised     = daily_impact   * 365

    return {
        "parameters": {
            "current_mix":               current_mix,
            "shift_from_channel":        shift_from_channel,
            "shift_to_channel":          shift_to_channel,
            "shift_pct":                 shift_pct,
            "foodpanda_commission_pct":  foodpanda_commission_pct,
            "own_delivery_cost_per_order":own_delivery_cost_per_order,
            "loyalty_incentive_cost":    loyalty_incentive_cost,
            "basket_value_change_pct":   basket_value_change_pct,
            "daily_transactions":        daily_transactions,
            "avg_basket_pkr":            avg_basket_pkr,
        },
        "outputs": {
            "actual_shift_applied_pct":   round(actual_shift * 100, 1),
            "new_channel_mix":            {k: round(v, 3) for k, v in new_mix.items()},
            "old_revenue_per_txn_pkr":    round(old_revenue_per_txn, 2),
            "new_revenue_per_txn_pkr":    round(new_revenue_per_txn, 2),
            "per_transaction_margin_change_pkr": round(per_txn_change, 2),
            "daily_impact_pkr":           round(daily_impact,   2),
            "annualised_pkr":             round(annualised,     2),
        },
    }
