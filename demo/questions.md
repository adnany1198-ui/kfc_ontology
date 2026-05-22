# KFC Pakistan Demo — Questions

18 questions across 6 blocks. Pacing: ~7 for the live 25-30 minute demo,
then open floor for Ahsan's questions.

---

## Block A — Warmup: Substrate Confirmation (Q1–3)
*Goal: establish credibility of the data. Show it's real, live, big.*

**Q1.** How many transactions do we have, from how many stores, over what date range?
What was yesterday's transaction count?

**Q2.** Show me the top 10 selling items by revenue across all stores.
Which category is driving the most of that?

**Q3.** What's our current split between cash and card payments, broken down by store?
Any stores that look unusual?

---

## Block B — Real Data Killers (Q4–8)
*Goal: show that unified data answers cross-dimensional questions instantly.*

**Q4.** What's the channel mix across the estate — EAT IN vs EAT OUT vs DRIVE THRU vs DELIVERY?
Which stores are most delivery-heavy? Which are most drive-thru?

**Q5.** Compare average basket value by channel. Does delivery really have a higher basket?
Show me the distribution, not just the mean.

**Q6.** Which store had the highest transactions-per-active-day? What's driving that —
volume of footfall or higher basket value?

**Q7.** Show me hourly transaction density across all stores. When is our true peak?
Is it consistent across stores or does it vary by archetype?

**Q8.** Who are our top 5 operators by transactions processed in the last 30 days?
What's their average basket value vs the estate average?

---

## Block C — Prism Join: Demographics (Q9–11)
*Goal: show what CV data adds on top of POS.*

**Q9.** What does the basket look like by age band? Do younger customers spend more
or less than 35-44s? What categories are they buying?

**Q10.** We have three store archetypes — urban_young, family_suburban, mixed.
What's the difference in channel mix and basket composition between them?

**Q11.** For store 0062, show me the demographic flow by hour. When does it skew young,
when does it skew family? What are the staffing implications?

---

## Block D — Waste + WasteRecoveryModel (Q12–13)

**Q12.** What is our current average waste logging compliance rate across stores?
Which stores are worst? What's the total unlogged variance in PKR terms?

**Q13.** *(Parametric)* If we improve waste logging compliance from the current average
to 90% across all 16 stores, what's the annual PKR recovery?
What does the payback look like if we invest 500,000 PKR in training?

*→ Run WasteRecoveryModel calibrated from substrate compliance and waste data.*

---

## Block E — Procurement Shocks + DemandShockModel + MarginModel Ripple (Q14–15)

**Q14.** Walk me through the procurement price history for poultry over the last 6 months.
Is the +32% shock visible in the data? What's our current exposure?

**Q15.** *(Parametric + Ripple)* What if poultry prices spike another 25% from here?
Which SKUs are most affected? What does that do to our gross margin?
How does that change the economics of SHARING vs ALA CARTE items?

*→ DemandShockModel (primary) → MarginModel (ripple).*
*Show all parameters inline. Tag which are defaults vs calibrated.*

---

## Block F — Synthesis with Ripple (Q16–18)
*Goal: show the cascade — one question triggers multiple model runs.*

**Q16.** *(Full ripple)* We're paying Foodpanda 30% commission on delivery orders.
If we shifted 20% of those to our own delivery channel at 150 PKR/order cost,
what's the daily and annual PKR impact? Then: does that shift require more
staff and tills at our busiest stores?

*→ ChannelMixModel (primary) → LabourModel + ThroughputModel (ripple).*
*Use real channel mix from substrate. Use real hourly demand for store 0062.*

**Q17.** *(Throughput ripple)* What happens if we add a third till to store 0062?
What's the new bottleneck — kitchen or cashier? How does that change staffing
requirements across the day?

*→ ThroughputModel (primary, calibrated from store 0062 peak demand) → LabourModel (ripple).*
*Show the before/after comparison.*

**Q18.** *(Open-ended insight)* Based on everything in this dataset, what's the
single highest-confidence unsurfaced opportunity you see?
Walk me through the data signals and the model that supports it.

*→ Agent picks the strongest signal. Could be: waste compliance delta across stores,
delivery-to-own migration economics, under-utilised peak capacity at specific stores,
demographic/channel mismatch at family_suburban archetypes, operator performance spread.*

---

## Pacing Guide

| Block | Questions | Suggested time |
|-------|-----------|----------------|
| A | Q1–3 | 5 min |
| B | Q4–5, Q7 (skip Q6, Q8) | 7 min |
| C | Q9–10 (skip Q11) | 5 min |
| D | Q12–13 | 5 min |
| E | Q15 (skip Q14) | 4 min |
| F | Q16 + Q18 (skip Q17) | 7 min |
| Open | Ahsan's questions | unlimited |

Total guided: ~33 min. Leave 15+ min for Ahsan.

---

## Honest gaps to surface proactively

- **Speed of service**: we have one timestamp (payment capture). True SoS needs
  KDS instrumentation. ~£800/store hardware + 2-week install.
- **Prism data**: synthetic (anchored to real POS, directional signal only).
  Real Prism deployment = in-store CV cameras + consent framework.
- **Procurement**: synthetic with real shock shapes. Live integration = ERP API.
- **Operator identity**: operator_id is real but we don't have names/shift maps.
