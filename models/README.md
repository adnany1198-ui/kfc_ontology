# Parametric Models — Reference

All models are pure Python functions: parameters in, dict out. No I/O, no SQL.
Each returns `{"parameters": {...}, "outputs": {...}}` so every assumption is visible.

Import:
```python
from models import ThroughputModel, MarginModel, DemandShockModel
from models import LabourModel, WasteRecoveryModel, ChannelMixModel, PromotionModel
from models import run_with_ripple, format_ripple_output
```

---

## ThroughputModel

**Question:** How many transactions/hour can a store handle?

**Parameters:**
| Name | Default | Notes |
|------|---------|-------|
| tills | 2 | Number of active cashier tills |
| cashier_throughput_per_hour | 60 | Transactions per cashier per hour |
| kitchen_stations | 4 | Parallel kitchen prep stations |
| avg_cook_time_seconds | 75 | Mean seconds per item to cook |
| avg_basket_items | 2.3 | Average items per basket (calibrate from substrate) |
| peak_demand_per_hour | None | If supplied, computes utilisation |

**Outputs:** cashier_capacity_per_hour, kitchen_capacity_per_hour,
bottleneck_throughput, bottleneck_resource, utilisation, headroom_pct

**Ripple → LabourModel**

Calibration: pull `peak_demand_per_hour` from HourlyDemand query per store.
`avg_basket_items` from `SELECT AVG(item_count) FROM pos_transactions WHERE store_id=?`.

---

## MarginModel

**Question:** What is gross margin given basket mix and food costs?

**Parameters:**
| Name | Default | Notes |
|------|---------|-------|
| basket_value | 850 PKR | Average basket value |
| category_mix | ALA CARTE 40%, MEAL BOX 30%, SHARING 20%, BEVERAGE 10% | Dict of category → fraction |
| food_cost_ratios | See defaults | Dict of category → cost ratio |

**Default food cost ratios:**
BEVERAGE 0.15, SOFT SERVE 0.18, ADD ON 0.20, SNACKS 0.25,
ALA CARTE 0.28, EDV 0.28, MEAL BOX 0.30, MAKE IT A MEAL 0.30, SHARING 0.32

**Outputs:** gross_margin_pkr, gross_margin_pct, total_cogs_pkr,
blended_food_cost_ratio, margin_by_category

**Ripple → none** (terminal model)

Calibration: `SELECT category, SUM(line_total) / total_basket_value FROM pos_line_items ...`

---

## DemandShockModel

**Question:** What if poultry/oil prices spike by X%?

**Parameters:**
| Name | Default | Notes |
|------|---------|-------|
| commodity | POULTRY_WHL | Commodity ID (see procurement_prices table) |
| pct_change | 0.32 | Fractional change (+0.32 = +32%) |
| sku_dependency_weights | Default SKU map | Dict of {sku: {commodity: weight}} |

**Outputs:** affected_skus, sku_cogs_impacts (per SKU), avg_cogs_change_pct,
avg_margin_compression_pct, affected_stores

**Ripple → MarginModel, ChannelMixModel**

Calibration: pull shock magnitude from `procurement_prices` table. Check
`spot_price_pkr` vs baseline for embedded Poultry (+32%) and Oil (+25%) shocks.

---

## LabourModel

**Question:** How should we staff given the expected demand curve?

**Parameters:**
| Name | Default | Notes |
|------|---------|-------|
| hourly_demand_curve | Synthetic 24-hour curve | List of 24 floats (txns/hour) |
| transactions_per_cashier_hour | 60 | Throughput per cashier |
| cashiers_per_shift | 3 | Current scheduling |
| shift_blocks | (7,15), (15,23), (23,7) | Shift start/end hours |
| wage_pkr_per_hour | 120 | Loaded wage per cashier |

**Outputs:** hourly_staffing (24-item list), total_daily_labour_cost_pkr,
over_staffed_hours, under_staffed_hours, peak_demand_hour

**Ripple → none** (terminal model)

Calibration: `SELECT hour, COUNT(*) FROM pos_transactions WHERE store_id=? GROUP BY hour`

---

## WasteRecoveryModel

**Question:** What is the PKR value of improving waste compliance?

**Parameters:**
| Name | Default | Notes |
|------|---------|-------|
| current_compliance_pct | 0.60 | Average log compliance across stores |
| target_compliance_pct | 0.90 | Target after intervention |
| avg_daily_waste_pkr | 15000 | Daily waste value per store |
| n_stores | 16 | Number of stores in scope |
| implementation_cost_pkr | 500000 | One-time training/system cost |

**Outputs:** compliance_gap_pct, pkr_recovery_per_store_per_day,
pkr_recovery_per_day, annualised_recovery_pkr, payback_estimate_days,
payback_estimate_months

**Ripple → none** (terminal model)

Calibration: `SELECT store_id, AVG(log_compliance) FROM inventory_movements GROUP BY store_id`
`SELECT store_id, SUM(ABS(variance_pkr)) / COUNT(DISTINCT date) FROM inventory_movements GROUP BY store_id`

---

## ChannelMixModel

**Question:** What happens if we shift X% of orders from Foodpanda to own delivery (or dine-in)?

**Parameters:**
| Name | Default | Notes |
|------|---------|-------|
| current_mix | EAT IN 40%, EAT OUT 20%, DRIVE THRU 15%, DELIVERY 25% | Dict |
| shift_from_channel | DELIVERY | Source channel |
| shift_to_channel | EAT IN | Target channel |
| shift_pct | 0.20 | Fraction to shift |
| foodpanda_commission_pct | 0.30 | Aggregator take rate |
| own_delivery_cost_per_order | 150 PKR | Own fleet marginal cost |
| loyalty_incentive_cost | 50 PKR | Cost to incentivise shift |
| basket_value_change_pct | 0.05 | Basket uplift in target channel |
| daily_transactions | 500 | Total daily transactions (all stores or selected) |
| avg_basket_pkr | 850 | Average basket value |

**Outputs:** actual_shift_applied_pct, new_channel_mix,
per_transaction_margin_change_pkr, daily_impact_pkr, annualised_pkr

**Ripple → LabourModel, ThroughputModel**

Calibration: pull current_mix from `store_summary` or
`SELECT channel, COUNT(*) FROM pos_transactions GROUP BY channel`

---

## PromotionModel

**Question:** What is the net P&L impact of discounting a SKU?

**Parameters:**
| Name | Default | Notes |
|------|---------|-------|
| target_sku | ZINGER_BURGER | SKU being discounted |
| discount_pct | 0.20 | Discount depth (0.20 = 20% off) |
| target_stores | 16 | Number of stores running promo |
| target_segment | all | Demographic target (informational) |
| attach_rate_assumption | 0.35 | Fraction of lift txns that attach a side/drink |
| base_daily_txns_per_store | 30 | Baseline daily txns of that SKU per store |
| avg_sku_price_pkr | 450 | Full price of target SKU |
| avg_basket_pkr | 850 | Average overall basket |
| food_cost_ratio | 0.28 | Food cost ratio for the SKU |
| transaction_lift_elasticity | 1.5 | Lift multiplier per % discount |

**Outputs:** transaction_lift_pct, lifted_transactions_per_day,
discounted_sku_price_pkr, margin_at_discount_pkr, net_pkr_impact_per_day,
annualised_pkr, margin_change_pct

**Ripple → MarginModel, ThroughputModel**

Calibration: pull base_daily_txns from
`SELECT COUNT(*) / COUNT(DISTINCT date) FROM pos_line_items WHERE product_name LIKE '%ZINGER%'`

---

## Ripple Orchestrator

```python
results = run_with_ripple(
    primary_model_name="ChannelMixModel",
    primary_inputs={"shift_pct": 0.20, "shift_from_channel": "DELIVERY"},
    downstream_inputs={
        "LabourModel": {"hourly_demand_curve": [...]},
        "ThroughputModel": {"tills": 3, "peak_demand_per_hour": 45},
    }
)
print(format_ripple_output(results))
```

**Ripple graph:**
```
ThroughputModel  → LabourModel
DemandShockModel → MarginModel, ChannelMixModel
PromotionModel   → MarginModel, ThroughputModel
ChannelMixModel  → LabourModel, ThroughputModel
MarginModel      → (terminal)
LabourModel      → (terminal)
WasteRecoveryModel → (terminal)
```
