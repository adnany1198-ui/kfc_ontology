def ThroughputModel(
    tills: int = 2,
    cashier_throughput_per_hour: float = 60,
    kitchen_stations: int = 4,
    avg_cook_time_seconds: float = 75,
    avg_basket_items: float = 2.3,
    peak_demand_per_hour: float = None,
):
    """
    Compute peak transactions/hour given till and kitchen capacity.
    Returns the bottleneck and utilisation per resource.
    """
    cashier_capacity = tills * cashier_throughput_per_hour
    kitchen_capacity = (kitchen_stations * 3600) / (avg_cook_time_seconds * avg_basket_items)
    bottleneck_capacity = min(cashier_capacity, kitchen_capacity)
    bottleneck_resource = "cashier" if cashier_capacity < kitchen_capacity else "kitchen"

    util = {}
    if peak_demand_per_hour is not None:
        util["cashier"] = round(peak_demand_per_hour / cashier_capacity, 3)
        util["kitchen"] = round(peak_demand_per_hour / kitchen_capacity, 3)

    headroom_pct = round((bottleneck_capacity - (peak_demand_per_hour or 0)) / bottleneck_capacity * 100, 1) \
        if peak_demand_per_hour is not None else None

    return {
        "parameters": {
            "tills":                        tills,
            "cashier_throughput_per_hour":  cashier_throughput_per_hour,
            "kitchen_stations":             kitchen_stations,
            "avg_cook_time_seconds":        avg_cook_time_seconds,
            "avg_basket_items":             avg_basket_items,
            "peak_demand_per_hour":         peak_demand_per_hour,
        },
        "outputs": {
            "cashier_capacity_per_hour":    round(cashier_capacity, 1),
            "kitchen_capacity_per_hour":    round(kitchen_capacity, 1),
            "bottleneck_throughput":        round(bottleneck_capacity, 1),
            "bottleneck_resource":          bottleneck_resource,
            "utilisation":                  util,
            "headroom_pct":                 headroom_pct,
        },
    }
