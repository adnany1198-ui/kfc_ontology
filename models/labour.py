def LabourModel(
    hourly_demand_curve: list = None,
    transactions_per_cashier_hour: float = 60,
    cashiers_per_shift: int = 3,
    shift_blocks: list = None,
    wage_pkr_per_hour: float = 120,
):
    """
    Compute recommended staffing per hour given expected transaction demand.
    hourly_demand_curve: list of 24 floats (transactions per hour by hour 0-23)
    shift_blocks: list of (start_hour, end_hour) tuples defining shift structure
    """
    if hourly_demand_curve is None:
        hourly_demand_curve = [
            5, 3, 2, 1, 1, 2, 5, 12, 18, 22, 28, 35,
            40, 38, 32, 28, 25, 30, 38, 42, 35, 25, 15, 8
        ]
    if shift_blocks is None:
        shift_blocks = [(7, 15), (15, 23), (23, 7)]

    if len(hourly_demand_curve) != 24:
        raise ValueError("hourly_demand_curve must have exactly 24 entries (one per hour)")

    hourly = []
    total_cost = 0.0
    total_over  = 0
    total_under = 0

    for hour, demand in enumerate(hourly_demand_curve):
        required_cashiers = demand / transactions_per_cashier_hour
        recommended = max(1, round(required_cashiers + 0.5))

        active_shift = None
        for start, end in shift_blocks:
            if start < end:
                if start <= hour < end:
                    active_shift = (start, end)
            else:
                if hour >= start or hour < end:
                    active_shift = (start, end)

        scheduled = cashiers_per_shift if active_shift else 1
        delta = scheduled - recommended

        if delta > 0:
            status = "over_staffed"
            total_over += 1
        elif delta < 0:
            status = "under_staffed"
            total_under += 1
        else:
            status = "optimal"

        cost_this_hour = scheduled * wage_pkr_per_hour
        total_cost += cost_this_hour

        hourly.append({
            "hour":               hour,
            "expected_demand":    round(demand, 1),
            "cashiers_required":  round(required_cashiers, 2),
            "cashiers_recommended": recommended,
            "cashiers_scheduled": scheduled,
            "status":             status,
            "cost_pkr":           round(cost_this_hour, 2),
        })

    peak_hour = max(range(24), key=lambda h: hourly_demand_curve[h])

    return {
        "parameters": {
            "hourly_demand_curve":          hourly_demand_curve,
            "transactions_per_cashier_hour":transactions_per_cashier_hour,
            "cashiers_per_shift":           cashiers_per_shift,
            "shift_blocks":                 shift_blocks,
            "wage_pkr_per_hour":            wage_pkr_per_hour,
        },
        "outputs": {
            "hourly_staffing":              hourly,
            "total_daily_labour_cost_pkr":  round(total_cost, 2),
            "over_staffed_hours":           total_over,
            "under_staffed_hours":          total_under,
            "optimal_hours":                24 - total_over - total_under,
            "peak_demand_hour":             peak_hour,
            "peak_demand_transactions":     round(hourly_demand_curve[peak_hour], 1),
        },
    }
