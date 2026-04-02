# 🧬 Methodology Deep-Dive

> **False Growth Early Warning System** — Identifying Employment Expansion that Masks Workforce Fragility

---

## The Core Question

| What everyone asks | What this project asks |
|---|---|
| *"Which metros are adding jobs?"* | *"Which metros are adding jobs **on a stable skill foundation**?"* |

Standard labor data measures **hiring volume**. This framework measures **workforce composition** — what we call **Skill DNA**.

---

## Data Architecture

<table>
<tr>
<th>Source</th>
<th>What It Provides</th>
<th>Grain</th>
<th>Years</th>
</tr>
<tr>
<td><b>O*NET</b></td>
<td>55 work context + 35 skill ratings per occupation</td>
<td>SOC code</td>
<td>Cross-sectional</td>
</tr>
<tr>
<td><b>BLS OEWS</b></td>
<td>Employment counts by occupation × metro area</td>
<td>SOC × MSA</td>
<td>2019, 2023</td>
</tr>
<tr>
<td><b>BLS Projections</b></td>
<td>Occupational separation rates (churn target)</td>
<td>SOC</td>
<td>2019, 2023</td>
</tr>
</table>

**Result:** 396 metro areas × 90 Skill DNA features + 1 churn target

---

## Model Comparison

| | Employment Growth Only | Skill DNA (Gradient Boosting) |
|---|:---:|:---:|
| **R²** | 0.052 | **0.768** |
| **ASE** | 0.190 | **0.046** |
| **Features** | 1 | 90 |
| **Interpretation** | Growth alone explains 5% of churn | Skill DNA explains **77% of churn** |
| **Improvement** | Baseline | **15× more explanatory power** |

### Why Gradient Boosting over Linear Regression?

| Factor | Linear Regression | Gradient Boosting |
|---|---|---|
| **Non-linear interactions** | ❌ Can't capture | ✅ Handles naturally |
| **Example** | — | Low autonomy + high time pressure compounds churn risk |
| **Overfitting risk** | Low | Managed (converged at 60 trees, stable train/validation error) |
| **Interpretability** | High | Moderate (feature importance available) |
| **Selected?** | Baseline only | ✅ **Primary model** |

---

## Quadrant Classification Logic

```
IF predicted_churn > MEDIAN(all_churn)
   AND employment_growth > MEDIAN(all_growth)
   → FALSE GROWTH

IF predicted_churn ≤ MEDIAN(all_churn)
   AND employment_growth > MEDIAN(all_growth)
   → TRUE GROWTH

IF predicted_churn > MEDIAN(all_churn)
   AND employment_growth ≤ MEDIAN(all_growth)
   → FRAGILE / DECLINE

ELSE → STABLE
```

### Why median splits (not k-means, not percentiles)?

| Approach | Pro | Con | Our choice? |
|---|---|---|:---:|
| **Median split** | Transparent, reproducible, balanced groups | Binary boundary | ✅ |
| **K-means** | Data-driven clusters | Opaque, sensitive to initialization | ❌ |
| **Percentile-based** | Adjustable thresholds | Arbitrary (why 75th vs 80th?) | ❌ |

---

## Validation Summary

| Test | Question | Result | Verdict |
|---|---|---|:---:|
| **Churn reality** | Do False Growth regions actually churn more? | 11.66% vs 10.99%, **p < 0.0001** | ✅ Real |
| **Employment illusion** | Can growth alone distinguish them? | 12.1% vs 10.3% — nearly identical | ⚠️ No |
| **Concentration** | Is this a fringe finding? | 114/187 high-growth metros = **61%** | ⚠️ Majority |

---

## Assumptions & Known Limitations

| Assumption | Risk | Mitigation |
|---|---|---|
| 2019 skill structure predicts 2023 churn | COVID may have introduced non-structural churn | Strict temporal holdout design; pandemic acts as natural experiment |
| Median split creates meaningful groups | A region at 51st pctile = same label as 99th | Future: continuous False Growth Index |
| MSA-level analysis only | Excludes rural and micropolitan areas | Data constraint (OEWS coverage) |
| Model generalizes beyond this window | Only tested on one 4-year window | Future: test 2015→2019 and 2023→2028 |

---

## What Would Make This Stronger

| Extension | What it adds | Effort |
|---|---|---|
| **Multi-window backtesting** (2015→2019, 2019→2023) | Tests if False Growth is persistent or pandemic-specific | Medium |
| **Industry decomposition** | Separates warehouse churn from healthcare churn | Medium |
| **Continuous False Growth Index** | Graduated risk score instead of binary label | Low |
| **Interactive dashboard** | Workforce board can filter by state/metro/industry | High |
| **Wage + job quality data** | Distinguishes low-wage churn from high-wage rotation | Medium |
