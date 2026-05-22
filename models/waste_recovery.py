def WasteRecoveryModel(
    current_compliance_pct: float = 0.60,
    target_compliance_pct: float = 0.90,
    avg_daily_waste_pkr: float = 15000,
    n_stores: int = 16,
    implementation_cost_pkr: float = 500000,
):
    """
    Estimate PKR recovery from improving waste logging compliance.
    Assumes logged waste is reduced/recovered; unlogged waste is invisible loss.
    """
    compliance_gap = target_compliance_pct - current_compliance_pct
    if compliance_gap <= 0:
        return {
            "parameters": {
                "current_compliance_pct":  current_compliance_pct,
                "target_compliance_pct":   target_compliance_pct,
                "avg_daily_waste_pkr":     avg_daily_waste_pkr,
                "n_stores":                n_stores,
                "implementation_cost_pkr": implementation_cost_pkr,
            },
            "outputs": {
                "pkr_recovery_per_day":    0,
                "pkr_recovery_per_store_per_day": 0,
                "annualised_recovery_pkr": 0,
                "payback_estimate_days":   None,
                "note": "Target compliance already met or exceeded.",
            },
        }

    recovery_per_store_per_day = avg_daily_waste_pkr * compliance_gap
    total_recovery_per_day     = recovery_per_store_per_day * n_stores
    annualised                 = total_recovery_per_day * 365

    payback_days = (
        implementation_cost_pkr / total_recovery_per_day
        if total_recovery_per_day > 0 else None
    )

    return {
        "parameters": {
            "current_compliance_pct":    current_compliance_pct,
            "target_compliance_pct":     target_compliance_pct,
            "avg_daily_waste_pkr":       avg_daily_waste_pkr,
            "n_stores":                  n_stores,
            "implementation_cost_pkr":   implementation_cost_pkr,
        },
        "outputs": {
            "compliance_gap_pct":             round(compliance_gap * 100, 1),
            "pkr_recovery_per_store_per_day": round(recovery_per_store_per_day, 2),
            "pkr_recovery_per_day":           round(total_recovery_per_day,     2),
            "annualised_recovery_pkr":        round(annualised,                 2),
            "payback_estimate_days":          round(payback_days, 1) if payback_days else None,
            "payback_estimate_months":        round(payback_days / 30, 1) if payback_days else None,
        },
    }
