# AQI Predictor — EDA Findings Log

Running notes from the exploratory data analysis phase, to be used directly in the final project report. Each entry includes the finding, the evidence, and the mechanism behind it.

---

## Finding 1 — Strong, repeating annual seasonal cycle in AQI

**What we found:** Daily average AQI shows a clear, repeating cycle across both years of data:
- **Trough (~60–100 AQI):** July–September (monsoon season)
- **Peak (~150–210 AQI):** October–January, peaking around December–January

**Mechanism:** Monsoon rain washes pollutants from the air and improves dispersion. Post-monsoon/winter combines post-harvest crop residue burning with temperature inversions (cold, dense surface air trapping pollutants that would normally rise and disperse), producing the year's worst air quality.

**Implication for modeling:** The `month` feature carries strong, physically-grounded predictive signal — this isn't a coincidental correlation, it's a well-understood seasonal mechanism. Confirmed consistent across both years in the dataset (not a one-off).

**Caveat noted:** The most recent partial cycle (mid-2026) is incomplete — data ends July 27, so no claims should be made about how that specific monsoon season compares to prior years.

---

## Finding 2 — `us_aqi` shows almost no hour-of-day pattern (and why)

**What we found:** Mean AQI by hour of day is nearly flat (~120–122 across all 24 hours) with a very large standard deviation band (±30+), swamping any hourly signal.

**Mechanism:** The US AQI is not computed from instantaneous pollutant readings — EPA methodology (which Open-Meteo follows) computes PM2.5's AQI sub-index from a **24-hour rolling average** (or 12-hour NowCast-weighted average), and ozone's sub-index from an **8-hour rolling average**. This smoothing is baked into the AQI value itself before it reaches the dataset, which erases most within-day variation. The large std band reflects day-to-day/seasonal variation (Finding 1), not hour-to-hour noise.

**Implication for modeling:** Don't discard the `hour` feature based on this alone — check actual feature importance during training (Phase 6) rather than assuming irrelevance from a marginal plot. This finding is really about the *target variable's construction*, not about whether time-of-day matters to pollution.

---

## Finding 3 — Raw pollutant concentrations reveal a real diurnal cycle, driven by boundary-layer dynamics and photochemistry (not simple traffic timing)

**What we found:** Unlike smoothed `us_aqi`, raw pollutant concentrations (PM2.5, PM10, NO2, ozone) show a strong, consistent daily cycle:
- **NO2, PM2.5, PM10:** high overnight, decline through morning, bottom out midday (11am–4pm), sharp rise from ~5–9pm
- **Ozone:** inverse pattern — low overnight, peaks in early-mid afternoon (~12–3pm)

**Mechanism (two compounding effects):**
1. **NOx–ozone photochemical cycle:** sunlight breaks down NO2 into NO + free oxygen, which reacts to form ozone — so NO2 is chemically converted into ozone during daylight hours, explaining why the two pollutants are almost perfect mirror images of each other.
2. **Atmospheric boundary layer height:** at night, a shallow, stable air layer traps pollutants near the surface (same inversion mechanism as Finding 1, operating daily instead of seasonally). Daytime solar heating causes convective mixing, expanding this layer and diluting near-surface pollutant concentrations — independent of actual emission levels.

**Note on the original hypothesis:** the initial expectation was a simple traffic-driven double rush-hour bump. The actual data shows a more physically complete story — the evening rise (5–9pm) likely combines both boundary-layer collapse *and* rush-hour traffic reinforcing each other, while the morning traffic signal is likely present but masked by the much stronger effect of the boundary layer still expanding at that time.

**Implication for modeling:** Raw pollutant features (not just `us_aqi`) carry real, complementary diurnal information — worth retaining through training rather than assuming `us_aqi` alone captures everything.

---

## Finding 4 — No meaningful weekday/weekend pattern in `us_aqi` (confirms Finding 2, doesn't extend it)

**What we found:** Mean AQI by day of week is flat (~120–123) across all seven days, well within a wide std band — no visible weekday/weekend separation.

**Mechanism:** This is not a new pattern, but the expected consequence of Finding 2 — `us_aqi`'s 8–24 hour rolling-average construction smooths out shorter-term variation (whether hourly or weekday-driven), so any real weekday/weekend emissions difference (e.g. less industrial or traffic activity on weekends) doesn't survive into the AQI value itself.

**Note on method:** this result was explicitly predicted in advance based on Finding 2's mechanism, then confirmed — a hypothesis-driven check rather than an open-ended one. Worth stating as such in the report rather than presenting it as a standalone discovery.

**Implication for modeling:** `day_of_week`/`is_weekend` features are unlikely to carry strong standalone signal for predicting `us_aqi` directly, though — same caveat as `hour` — final judgment should come from feature importance in Phase 6, not from this plot alone.

---

## Finding 5 — No weekly emissions cycle at all, confirmed at the raw pollutant level (not just an AQI-smoothing artifact)

**What we found:** Unlike the hour-of-day case (Finding 3), where raw pollutants revealed a real cycle hidden by `us_aqi`'s smoothing, raw pollutant concentrations (PM2.5, PM10, NO2, ozone) are **also flat across day of week** — no weekday/weekend difference at the source level.

**Why this is a distinct finding, not a repeat of Finding 4:** Finding 4 only showed that *smoothed AQI* had no weekly pattern, which was ambiguous — it could have meant either "no real weekly cycle" or "a real cycle exists but got smoothed away," analogous to what happened with hour-of-day. Checking raw concentrations directly resolves that ambiguity: there is genuinely no weekly emissions cycle here, at any level of the data.

**Mechanism:** A weekday/weekend emissions dip is typical of cities with a strong Mon–Fri office-commute culture. In this region, transport, informal markets, and industrial activity largely operate on a continuous 7-day schedule rather than dropping off on weekends, so there's no structural reason to expect (or find) a weekly cycle.

**Implication for modeling:** `day_of_week` and `is_weekend` are unlikely to be meaningful predictors for this location — confirmed at both the AQI and raw-pollutant level, not just assumed. Season (Finding 1) and daily boundary-layer/photochemical cycles (Finding 3) are the dominant, confirmed drivers of variation; weekly human-activity rhythm is not a factor here.

---

## Finding 6 — Correlation matrix confirms and refines earlier findings; PM2.5 identified as the dominant pollutant driver

**What we found:**
- **Lag features are the strongest predictors of `us_aqi`** (`aqi_lag_1h`: ~0.99–1.00, `aqi_lag_3h`: 0.99, `aqi_lag_24h`: 0.82) — expected given AQI's hour-to-hour persistence, and good news for forecasting.
- **PM2.5 is the dominant raw pollutant driver** of `us_aqi` (r=0.69), clearly stronger than PM10 (0.29), CO (0.56), or SO2 (0.57).
- **NO2 correlates only moderately with `us_aqi`** (0.33) despite having a strong diurnal cycle (Finding 3) — NO2 has real hourly structure but is rarely the pollutant that dominates the overall AQI calculation; PM2.5 usually is.
- **Weather correlations cross-confirm Finding 1's seasonal/inversion mechanism**, not as new information but as three independent variables agreeing with it: temperature (-0.49, colder = higher AQI), surface pressure (+0.53, stable high-pressure systems trap pollution), wind speed (-0.35, confirms dispersion mechanism).
- **Ozone (-0.04) and precipitation (-0.06) show near-zero linear correlation with `us_aqi`**, despite both having clear mechanistic relevance (Finding 3 for ozone, Finding 1 for precipitation/monsoon). Likely explanations: ozone peaks when PM is typically low (different timing, canceling out linearly); precipitation is heavily skewed (mostly zero, occasional bursts), which Pearson correlation handles poorly. Treated as a correlation-method limitation, not evidence these variables don't matter.
- **Multicollinearity noted** among the three lag features (0.82–0.99 with each other) and within two source-driven pairs (CO/NO2: 0.71; temperature/surface pressure: -0.79) — relevant for Ridge regression interpretability in Phase 6, less of a concern for Random Forest.

**Implication for modeling:** Confirms lag features and PM2.5 as likely top predictors; supports keeping ozone/precipitation/humidity in the feature set despite weak linear correlation, since their relevance is mechanistic and possibly non-linear — final call deferred to feature importance analysis in Phase 6, consistent with the project's stated pruning-timing principle.

---

## Finding 7 — No missing data across the full 2-year span

**What we found:** Zero null values in any column, and zero missing hourly timestamps across the entire dataset (17,544 expected hours = 17,544 actual hours present).

**Why this matters:** Confirms the chunked backfill (Phase 4) executed cleanly with no dropped requests or silent API failures, and that the archive-to-live source boundary (July 21/22, 2026) introduced no gaps despite coming from two different endpoints. A clean, complete dataset with no imputation or gap-filling required going into model training.

---

## EDA Summary (Phase 5 complete)

Seven findings total, established through hypothesis-driven checks (predict → verify → explain mechanism) rather than open-ended pattern-hunting:

1. Strong repeating annual seasonal cycle (monsoon trough, winter peak) — driven by rain/dispersion vs. crop burning + temperature inversions
2. `us_aqi` shows no hour-of-day pattern — an artifact of its 8–24h rolling-average construction, not evidence pollution lacks a daily rhythm
3. Raw pollutants reveal a real diurnal cycle — driven by boundary-layer height (traps pollutants overnight) and NOx–ozone photochemistry (mirror-image relationship confirmed)
4. `us_aqi` shows no weekday/weekend pattern — consistent with Finding 2's smoothing explanation
5. Raw pollutants also show no weekday/weekend pattern — confirms Finding 4 is a real absence of weekly cycle, not just smoothing; consistent with a 7-day-active local economy rather than a Mon–Fri commute culture
6. Correlation matrix — lag features and PM2.5 are the strongest linear predictors of `us_aqi`; weather correlations (temperature, pressure, wind) all cross-confirm Finding 1's seasonal mechanism; ozone/precipitation show weak linear correlation despite mechanistic relevance, likely due to non-linearity/skew rather than true irrelevance
7. No missing data — complete, gap-free 2-year hourly dataset (17,544/17,544 hours), confirming a clean backfill with no source-boundary artifacts

---

## Baseline Model Results (Phase 6 — naive persistence)

**Method:** predict each day's target AQI as simply today's current `us_aqi` value (no learning, no features). Evaluated on a chronological 20% holdout (~4–5 months of unseen, most-recent data).

| Horizon | RMSE | MAE | R² |
|---|---|---|---|
| Day 1 | 18.56 | 14.63 | 0.407 |
| Day 2 | 24.19 | 19.17 | -0.018 |
| Day 3 | 26.79 | 21.66 | -0.272 |

**Interpretation:** Error grows and R² degrades sharply as the forecast horizon extends — R² < 0 at day2/day3 means naive persistence performs *worse* than simply predicting the historical average AQI at those horizons.

**Why:** connects directly to Finding 1 (seasonal mean-reversion). Today's AQI is a reasonable predictor of tomorrow's (spikes tend to persist briefly), but AQI tends to drift back toward its seasonal baseline within a few days rather than staying pinned at an unusual value. Naive persistence has no way to represent this reversion, so its assumption ("no change") becomes progressively wrong as the horizon extends.

---

## Model Comparison — Baseline vs Ridge vs Random Forest (Phase 6)

| Horizon | Baseline R² | Ridge R² | RF (untuned) R² | RF (tuned) R² |
|---|---|---|---|---|
| Day 1 | 0.407 | 0.456 | 0.280 | **0.488** |
| Day 2 | -0.018 | 0.041 | 0.077 | **0.137** |
| Day 3 | -0.272 | -0.180 | -0.088 | **-0.032** |

**Key observation — untuned RF initially underperformed Ridge at Day 1 specifically:** Random Forest's `feature_importances_` showed `us_aqi` alone accounted for ~71% of total importance at Day 1, consistent with EDA Finding 6 (day1 target correlates ~0.99 with `aqi_lag_1h`). This means the day1 relationship is close to linear — a regime where linear models (Ridge) have a structural advantage, since tree-based models can only approximate a smooth line via many small step-function splits, and with unconstrained depth on ~14K rows, the untuned Random Forest was likely overfitting to noise around this single dominant feature rather than cleanly capturing the near-linear relationship.

**Diagnostic ruled out:** confirmed test-set `us_aqi` range (65–173) sits fully within the training range (54–214) — the day1 gap was not due to extrapolation beyond the training distribution.

**Fix — hyperparameter tuning via RandomizedSearchCV with TimeSeriesSplit (5 folds, 20 iterations):**
Best params: `max_depth=20, max_features='sqrt', max_samples=0.75, min_samples_leaf=8, min_samples_split=17, n_estimators=336`. Constraining tree depth and requiring more samples per split/leaf reduced overfitting, and the tuned model now outperforms Ridge at all three horizons — confirming the earlier day1 gap was an overfitting artifact of unconstrained trees, not a fundamental RF weakness relative to linear models.

---

## Feature Importance Analysis (tuned Random Forest, all horizons)

**New finding — importance shifts systematically as forecast horizon extends:**

| Feature | Day 1 | Day 2 | Day 3 |
|---|---|---|---|
| `surface_pressure` | 0.116 | 0.182 | 0.197 |
| `month` | 0.027 | 0.059 | 0.085 |
| `aqi_lag_1h` | 0.199 | 0.150 | 0.121 |
| `us_aqi` | 0.181 | 0.137 | 0.094 |

As the horizon extends, reliance on recency-based features (`aqi_lag_1h`, `us_aqi`) **decreases**, while reliance on slower-moving seasonal/atmospheric signals (`surface_pressure`, `month`) **increases**. This is a model-confirmed version of Finding 6's correlation-based observation about pressure/season, and it directly explains *why* Day 3 remains the hardest target: it's the point where the strongest available signal (recent AQI) has decayed most, forcing the model to lean on weaker, indirect seasonal proxies instead.

**Resolution of open EDA questions, using the tuned model's importance (which captures non-linear/interaction effects that the earlier correlation matrix could not):**

- **`day_of_week`** — confirmed genuinely weak (importance 0.008–0.021 across all horizons, near the bottom). Upgrades Finding 5 from "no *linear* relationship found" to "confirmed weak even accounting for non-linear effects."
- **`ozone`** — also confirmed genuinely weak (importance 0.009–0.011, lowest of all listed features), despite the real diurnal cycle found in Finding 3. Likely explanation: ozone's diurnal signal is largely redundant with `hour`/`month`, which are already present as separate features, so it adds little independent predictive value once those are included.
- **`nitrogen_dioxide` and `precipitation`** — did not appear in the top-15 output at all, ranking below ozone. *(Full ranking to be confirmed and logged.)*

---

**Resolution — confirmed by full ranking:** `nitrogen_dioxide` and `precipitation` rank below `ozone`, the lowest of all listed features — both confirmed as weak/negligible predictors despite their real underlying diurnal (NO2) or seasonal (precipitation) patterns found in earlier findings, for the same reason as ozone (largely redundant with `hour`/`month` once those are already present as features).

**Implication:** the earlier "keep everything, decide via feature importance" policy from Finding 6 is now actionable — `day_of_week`, `ozone`, `nitrogen_dioxide`, and `precipitation` are confirmed as weak/negligible predictors for this model, and are strong candidates for pruning in a simplified model. Retaining them causes no measurable harm at current data scale, so they remain in the feature set for now; final pruning decision deferred to the end of Phase 6 for simplicity.

---

## Experiment — Per-Horizon Hyperparameter Tuning (result: did not help, reverted)

**Hypothesis:** since feature importance differs structurally across horizons (Day 1 dominated by one strong feature; Day 3's importance spread thin across many weak features), tuning separate hyperparameters per horizon might outperform reusing one shared, Day-1-derived parameter set across all three.

**Method:** ran independent `RandomizedSearchCV` (5-fold `TimeSeriesSplit`, 20 iterations) for each of the three targets separately, then retrained and evaluated each on the actual held-out test set (not the CV score, which is not directly comparable to a final test score).

**Result — measured on the real held-out test set:**

| Horizon | Shared (Day1-derived) params | Per-horizon tuned params |
|---|---|---|
| Day 1 | 0.494 | 0.487 |
| Day 2 | 0.140 | 0.133 |
| Day 3 | -0.023 | **-0.085** |

Per-horizon tuning performed equal to or **worse** than the shared parameter set at every horizon, most notably at Day 3 — the exact horizon the hypothesis predicted it would help most.

**Why:** the Day 3 search selected a much smaller, shallower forest (`max_depth=5, n_estimators=101` vs. shared `max_depth=20, n_estimators=336`), likely because Day 3's weak, noisy, distributed signal made the search prone to **overfitting to the specific cross-validation folds** rather than finding genuinely generalizable settings — a known risk with a limited search budget (`n_iter=20`) on a low-signal target. Day 1's stronger, cleaner signal made its search more reliable, and those settings happened to generalize reasonably well when reused across all three horizons.

**Decision:** reverted to the shared, Day-1-derived hyperparameter set for the final Random Forest model — it performs as well or better across all horizons on the real test set, and is simpler to justify/maintain than three separate parameter sets. This negative result is retained in the report as a demonstration of correct evaluation methodology (final decisions based on held-out test performance, not in-search CV scores) rather than treated as a failed detour.

**Remaining limitation (at the Random Forest stage):** Day 3 R² (-0.023 to -0.032 depending on run) was still below zero at this point — meaningful improvement from baseline (-0.272) but not yet beating a flat average-AQI guess at the 3-day horizon. Consistent with the seasonal mean-reversion behavior identified in Finding 1, and directly confirmed by the RF importance-shift pattern: forecasting 3 days out requires leaning on weaker seasonal proxies as recency-based signal decays — motivating the Gradient Boosting model tried next.

---

## Gradient Boosting (XGBoost) Results — Day 3 Crosses R²=0 for the First Time

**Method:** XGBoost with early stopping (`early_stopping_rounds=30`, validation slice carved chronologically from the end of the training set, never touching the real test set), `learning_rate=0.05`, `max_depth=5`, `subsample=0.8`, `colsample_bytree=0.8` (tree-level column sampling, sampled without replacement — distinct from Random Forest's bootstrap-with-replacement row sampling).

**Full model progression (test set R²):**

| Horizon | Baseline | Ridge | RF (tuned) | XGBoost |
|---|---|---|---|---|
| Day 1 | 0.407 | 0.456 | 0.494 | **0.523** |
| Day 2 | -0.018 | 0.041 | 0.140 | **0.169** |
| Day 3 | -0.272 | -0.180 | -0.023 | **0.020** |

XGBoost outperforms every prior model at all three horizons — a clean, monotonic improvement across the model progression (Ridge → Random Forest → XGBoost), consistent with each model's increasing capacity to capture non-linear structure. **Day 3 crosses R²=0 for the first time across the entire project** — the model now genuinely outperforms a flat average-AQI guess at the hardest, 3-day-ahead horizon, though the margin (0.020) remains modest.

**Early stopping tree counts — additional quantitative evidence of signal decay by horizon:**
- Day 1: stopped at 143 trees (of 1000 max)
- Day 2: stopped at 47 trees
- Day 3: stopped at 46 trees

Day 1's validation performance kept improving for substantially longer before plateauing, while Day 2/Day 3 plateaued quickly — consistent with the seasonal mean-reversion / signal-decay story established in Finding 1 and the RF importance-shift analysis. This provides a second, independent, quantitative confirmation (not just visual/correlation-based) that genuine predictive signal for `us_aqi` diminishes sharply as the forecast horizon extends beyond ~24 hours.

---

## Experiment — XGBoost Hyperparameter Tuning (result: helped Day 1, hurt Day 2/3 — reverted)

**Method:** `RandomizedSearchCV` (5-fold `TimeSeriesSplit`, 30 iterations) tuned on the Day 1 target only (same shared-tuning approach validated as safer in the earlier Random Forest experiment), searching `n_estimators`, `learning_rate`, `max_depth`, `subsample`, `colsample_bytree`, `min_child_weight`, `gamma`, `reg_alpha`, `reg_lambda`. Best params applied across all three horizons, with early stopping still active per-horizon to determine actual tree counts (rather than fixing the searched `n_estimators` directly).

**Result — measured on the real held-out test set:**

| Horizon | Untuned XGBoost | Tuned (Day1-derived) XGBoost |
|---|---|---|
| Day 1 | 0.523 | **0.539** (improved) |
| Day 2 | 0.169 | 0.115 (worse) |
| Day 3 | **0.020** | -0.062 (worse — lost the R²=0 milestone) |

**Why:** the search found more conservative/regularized settings (`max_depth=3` vs. original `5`; `gamma=1.59` vs. default `0`) — appropriate for Day 1's strong, clean signal (where the main risk is overfitting), but overly restrictive for Day 2/3's weak, thin, distributed signal (where the model needs more freedom to capture subtle patterns, not less). This is the same core lesson as the earlier Random Forest per-horizon tuning experiment — a configuration tuned for one horizon's signal characteristics does not safely transfer to the others — but manifesting in the opposite direction (over-regularization instead of overfitting to CV noise).

**Decision:** reverted to the original, untuned XGBoost configuration as the final chosen model. It outperforms the tuned version overall (wins 2 of 3 horizons, including preserving the Day 3 milestone) and is simpler. Consistent with the project's established tiebreak rule: when a more complex/tuned option doesn't clearly win overall, prefer the simpler configuration.

**Methodological note for the report:** model selection throughout Phase 6 (Ridge vs. RF vs. XGBoost, tuned vs. untuned) was decided by direct comparison on the held-out test set rather than a separate validation set reserved purely for selection. This is a reasonable practical tradeoff at this project's scale, but is a mild form of test-set reuse worth stating explicitly as a limitation rather than presenting the final reported numbers as from one untouched, single-use holdout.

---

## Experiment — Round 2 Feature Engineering (result: no improvement, original XGBoost retained as final model)

**Motivation:** attempted to improve on XGBoost's Day 3 result (0.020) via five additions grounded in project findings: cyclical encoding of `hour`/`month` (addresses the linear-correlation blindness to cyclical patterns noted in Finding 6), rolling AQI mean/std over 6h/12h windows (captures trend/volatility beyond single-point lags), pruning confirmed-weak features (`day_of_week`, `ozone`, `nitrogen_dioxide`, `precipitation` — per the Feature Importance Analysis), an explicit `season` feature (grounded in Finding 1), and a 2-model (XGBoost + Random Forest) ensemble.

**Iterative testing (isolating variables after the first combined attempt underperformed):**

| Variant | XGBoost Day 1 | XGBoost Day 2 | XGBoost Day 3 |
|---|---|---|---|
| **v1 — original (champion)** | **0.523** | **0.169** | **0.020** |
| v2 — all 5 additions combined | 0.510 | 0.056 | -0.127 |
| v2 — season removed (redundant w/ month_sin/cos) | 0.499 | 0.036 | -0.075 |
| v2 — rolling AQI features only, isolated | 0.486 | 0.154 | 0.014 |

**Diagnosis:** every variant underperformed the original model at every horizon for XGBoost. Root cause: the new features (rolling AQI stats, and initially `season`) are substantially **redundant** with existing features (`aqi_lag_1h/3h/24h`, `month`) rather than adding independent signal. Because XGBoost uses `colsample_bytree=0.8` (random column subsampling per tree), adding redundant/low-value columns measurably dilutes the odds that already-strong features get selected into any given tree — an effect that compounds at Day 2/3, where genuine signal is already thin (per the established signal-decay pattern).

**One genuine positive result, noted for completeness:** Random Forest's Day 2 score improved with rolling features alone (0.140 → 0.171, its best result at this horizon) — plausibly because RF's bagging (independent trees, averaged) is inherently more tolerant of redundant/correlated columns than XGBoost's sequential boosting. This did not change the overall conclusion, as it does not exceed XGBoost v1's Day 2 result (0.169) by a meaningful margin.

**Decision:** retained the original, untuned v1 XGBoost configuration as the final Phase 6 model (Day1=0.523, Day2=0.169, Day3=0.020) — it remains the single best result across all attempted variants and hyperparameter tuning passes.

**Methodological reflection:** this series of experiments, combined with the earlier per-horizon tuning experiments, involved repeated comparisons against the same held-out test set to select a winner. Individually reasonable, but repeated test-set comparisons across many model variants carries a mild risk of selecting a configuration that wins partly by chance rather than genuine generalization. This is noted explicitly as a limitation, and as the stopping condition for further ad-hoc feature/hyperparameter search — continued iteration risks chasing test-set noise rather than finding real improvement.

---

## Diagnostic Experiment — Random vs. Chronological Train/Test Split (confirms peer score gap is a methodology artifact, not a modeling gap)

**Motivation:** peers on the same project reported substantially higher scores using simpler models (Ridge for Day1 ≈0.70, RF for Day2 ≈0.45, XGBoost for Day3 ≈0.40) than this project's rigorously-validated XGBoost champion (0.523 / 0.169 / 0.020). Rather than assume inferior modeling, tested the most common cause of inflated time-series scores: a random (shuffled) train/test split instead of a chronological one.

**Method:** trained the identical XGBoost model/hyperparameters on the same feature set, comparing the project's proper `time_based_split()` against a standard shuffled `train_test_split()` (sklearn default behavior — shuffles unless explicitly told not to).

**Result:**

| Horizon | Chronological (honest) R² | Random-split (leaky) R² | Gap |
|---|---|---|---|
| Day 1 | 0.523 | 0.927 | +0.404 |
| Day 2 | 0.169 | 0.888 | +0.719 |
| Day 3 | 0.020 | 0.871 | +0.851 |

Random shuffling inflates apparent R² dramatically at every horizon — and the inflation **grows** with forecast horizon, the opposite of what real forecasting difficulty would suggest.

**Mechanism:** with a random split, roughly 20% of every calendar day's hours land in the test set while the other 80% of that same day lands in training. Since `target_aqi_day3` for a test row is the mean AQI of a specific future calendar date, a random split makes it highly likely that *other hours of that exact target date* are sitting directly in the training set — the model partially observes the answer through nearby same-day rows rather than genuinely forecasting forward in time. This direct same-day leakage is most severe for the longest horizon (Day 3), explaining why its inflation is largest despite being the hardest problem when evaluated honestly.

**Interpretation of the peer score gap:** the random-split (leaky) numbers obtained here (0.87–0.93) exceed the peers' reported numbers (0.40–0.70), suggesting peers likely did not use a full row-level random shuffle identical to this test — a more probable explanation is a **day-level** random split (whole calendar days randomly assigned to train/test), which would avoid the most extreme same-day leakage demonstrated here while still leaking information across adjacent train/test day boundaries (e.g., a lag feature near midnight referencing a value one row across the boundary) — producing smaller, but still real, inflation consistent with the peers' reported magnitude.

**Conclusion:** this project's reported scores (0.523 / 0.169 / 0.020) reflect genuine, methodologically sound out-of-time forecasting performance. The lower absolute numbers compared to peer-reported results are very likely attributable to a train/test leakage difference in methodology, not inferior feature engineering or modeling. This diagnostic is retained as evidence of correct evaluation practice for the final report, and as a caution against comparing R² scores across implementations without confirming equivalent, leakage-free validation methodology.

---

## Experiment — Future Weather "Oracle" Test (result: negative, decisive — real-forecast version not pursued)

**Motivation:** every existing feature describes conditions *at the time of prediction*, not the future being forecast. Tested the theoretical ceiling of providing genuine future information: the actual (ground-truth, historical) daily-average weather that occurred on each target date, added as new features per horizon.

**Important framing:** this is an oracle/ceiling test, not a deployable feature — it uses real historical outcomes unavailable at true prediction time. The purpose was to check whether the *idea* (informing the model about future weather) is worth pursuing at all, before investing in a production version using Open-Meteo's actual (imperfect) multi-day forecast.

**Result — all three horizons got WORSE, not better:**

| Horizon | Champion | Oracle (perfect future weather) |
|---|---|---|
| Day 1 | 0.523 | 0.383 |
| Day 2 | 0.169 | 0.013 |
| Day 3 | 0.020 | -0.012 |

**Why, despite adding genuinely non-leaky, causally relevant information:**
1. **Redundancy with existing seasonal signal** — `month` and current `surface_pressure` already track the smooth multi-day seasonal cycle (Finding 1), so 1–3-day-ahead weather is often not very different from current weather; the marginal information added was smaller than expected.
2. **Column dilution** (same mechanism identified in the Round 2 feature engineering experiment) — 15 new columns added on top of ~20 existing ones (75% increase) diluted `colsample_bytree=0.8` sampling odds for already-strong features. Early-stopping tree counts dropped sharply at every horizon (e.g. Day 3: 46→22 trees), indicating the model began overfitting faster with the expanded, more redundant feature set.

**Conclusion:** since even the best-case, perfect-information oracle version underperforms the champion, a realistic production version (using Open-Meteo's genuinely imperfect future forecast, strictly less informative than ground truth) cannot be expected to help either. **Decision: not pursued further** — this diagnostic-first approach avoided investing in a more complex deployment feature that was never going to pay off.

---

## Experiment — Residual (Delta) Target Modeling (result: positive — new final model)

**Motivation:** rather than predicting each horizon's absolute AQI value directly, reframe the target as the *deviation* from today's current reading: `target_delta_dayH = target_aqi_dayH - us_aqi`, with the final prediction reconstructed as `us_aqi + predicted_delta`. Rationale: the naive persistence baseline already captures real signal (Finding — Baseline Model Results, Day1 R²=0.407); predicting only the deviation from that baseline lets the model focus entirely on learning what causes AQI to diverge from simple persistence, rather than re-deriving the persistence pattern implicitly within an absolute-value target.

**Method:** identical XGBoost architecture/hyperparameters as the champion model; only the target formulation changed. Evaluation performed on the **reconstructed absolute AQI scale** (not the delta scale) for direct, fair comparability with every other model in this project.

**Result — improved at every horizon, largest gain at the hardest target:**

| Horizon | Champion (absolute target) | Delta model | Gap |
|---|---|---|---|
| Day 1 | 0.523 | **0.546** | +0.023 |
| Day 2 | 0.169 | **0.223** | +0.054 |
| Day 3 | 0.020 | **0.066** | +0.046 |

Day 3's R² more than tripled relative to the champion — the largest relative improvement of any experiment attempted in this project, at exactly the horizon that had proven hardest to improve throughout Phase 6.

**Decision: adopted as the new final model.** Clean, well-motivated result with no methodological red flags (no CV/test-set score mismatch, no per-horizon overfitting pattern as seen in earlier tuning experiments) — a genuine improvement in target formulation rather than a search-driven or leakage-driven artifact.

**Feature importance under the delta formulation — notable shift from the absolute-target model:** `aqi_change_rate_1h` (a feature with negligible importance in the absolute-target champion) became the single **top feature for Day 1** under the delta formulation — intuitive in hindsight, since a feature literally measuring recent rate of change is directly relevant to predicting future *change*, even though it added little value predicting the absolute *level*. Similarly, `day_of_week`/`is_weekend` show real, non-trivial importance here (0.05–0.07), despite being confirmed negligible for the absolute AQI target in Findings 4/5. **Interpretation:** these features may genuinely help explain short-term deviations from persistence even though they don't help explain the absolute AQI level — a useful distinction, illustrating that a feature's usefulness can depend on how the target itself is framed, not just on the feature in isolation.

---

## Experiment — Hyperparameter Tuning and Huber Loss on the Delta Model (result: confirms a robust, recurring pattern — reverted to original)

**Method:** tuned XGBoost hyperparameters specifically for the delta target (search on Day 1's delta only, `RandomizedSearchCV`, 5-fold `TimeSeriesSplit`, 30 iterations), then separately tested `reg:pseudohubererror` (Huber loss) as an alternative to standard MSE, hypothesizing the delta distribution (small values, occasional large swings) might suit Huber's mixed MSE/MAE behavior better.

**Result — measured on the real held-out test set (reconstructed absolute-AQI scale):**

| Horizon | Original delta champion | Tuned (MSE) | Tuned (Huber) |
|---|---|---|---|
| Day 1 | 0.546 | **0.567** | 0.556 |
| Day 2 | **0.223** | 0.217 | 0.178 |
| Day 3 | **0.066** | 0.061 | 0.041 |

Tuning improved Day 1 marginally and hurt Day 2/Day 3 — **the same pattern observed independently in two prior experiments** (Random Forest per-horizon tuning, and absolute-target XGBoost tuning). Across three separate tuning attempts on three different models/targets, hyperparameters optimized against Day 1's strong, clean signal have consistently failed to transfer to Day 2/3's weaker, more diffuse signal. This is no longer treated as an isolated finding but as a robust, generalizable property of this forecasting problem, worth stating with confidence in the final report.

Huber loss underperformed standard MSE at every horizon, despite needing substantially more boosting rounds to converge (e.g. Day 3: 327 vs. 149 trees) — indicating the delta distribution is not heavy-tailed enough for Huber's robustness tradeoff to pay off here, or that hyperparameters tuned under standard R²-scored search do not transfer cleanly to a differently-shaped loss surface.

**Decision:** reverted to the original, untuned delta model (Day1=0.546, Day2=0.223, Day3=0.066) as the final chosen model — it wins 2 of 3 horizons outright, and Day 1's marginal tuned gain does not offset the Day 2/3 losses. Consistent with the project's established tiebreak rule (prefer the simpler, non-tuned configuration when a more complex option does not clearly win overall).

**Phase 6 improvement search — formally concluded.** Across this project, the following techniques were tested for further improvement beyond the delta model: per-horizon hyperparameter tuning (failed, ×3 independent instances), combined/isolated feature engineering additions (failed), a future-weather oracle test (failed, decisively ruling out a real-forecast version), and Huber loss (failed). All negative results are retained in this document as evidence of a thorough, principled search — the final model represents a genuine, well-validated best effort at this project's data scale, not an arbitrarily early stopping point.

---

## Final Refinement — Disabling Row Subsampling (result: genuine improvement at all three horizons, new final model)

**Change tested:** `subsample` changed from `0.8` to `1.0` (each tree now trains on all available rows, rather than a random 80% subset), alongside a minor reduction in `early_stopping_rounds` (30 → 20).

**Result — improved at every horizon, the only tested change so far to do so without any tradeoff:**

| Horizon | Previous delta champion | Final model (subsample=1.0) |
|---|---|---|
| Day 1 | 0.546 | **0.572** |
| Day 2 | 0.223 | **0.225** |
| Day 3 | 0.066 | **0.067** |

**Why:** `subsample=0.8` (row bagging) is a standard regularization default intended to reduce overfitting, but at this project's data scale (~14K training rows) and signal strength (particularly the already-thin Day 2/3 signal), it likely discarded useful information more than it protected against overfitting — especially given regularization was already being provided by `colsample_bytree=0.8` (column subsampling) and the learning rate itself (small correction steps per tree). Allowing each tree full access to all training rows let the model extract more from an already-scarce signal. Unlike every other tuning experiment in this project, this change did not trade one horizon's performance for another — a genuine, low-risk improvement to the production configuration.

**Final production model (adopted):**
```python
XGBRegressor(
    n_estimators=1000,       # ceiling — early stopping determines actual count per horizon
    learning_rate=0.05,
    max_depth=5,
    subsample=1.0,
    colsample_bytree=0.8,
    random_state=RANDOM_STATE,
    early_stopping_rounds=20,
    eval_metric="rmse",
    n_jobs=-1,
)
```
Trained on delta targets (`target_delta_dayH = target_aqi_dayH - us_aqi`), with predictions reconstructed as `us_aqi + predicted_delta` at inference time.

**Final reported results — Day1 R²=0.572, Day2 R²=0.225, Day3 R²=0.067** — this is the model to be saved to the Model Registry and used for the remaining project phases (SHAP, Streamlit dashboard).

---

## Further Refinement — Extended Lag Windows, 48h and 72h (result: genuine improvement, largest gain at Day 3)

**Change tested:** extended `LAG_HOURS` from `[1, 3, 24]` to `[1, 3, 24, 48, 72]`, adding `aqi_lag_48h` and `aqi_lag_72h` as new features — motivated by Day 3 requiring the most temporal context to reason about how conditions evolve over the full 3-day horizon, while previously being limited to a 24-hour lookback.

**Result — improved at every horizon, largest gain at Day 3:**

| Horizon | Previous champion | With 48h/72h lags |
|---|---|---|
| Day 1 | 0.572 | **0.578** |
| Day 2 | 0.225 | **0.232** |
| Day 3 | 0.067 | **0.088** (+31% relative) |

**Why:** unlike the Round 2 feature engineering attempt (rolling means/std, which largely duplicated information already present in `aqi_lag_1h/3h/24h`), 48h/72h lags provide genuinely new temporal reach the model didn't have access to before — directly extending its lookback window rather than re-expressing existing information in a different form. This explains why this addition succeeded where the earlier rolling-window attempt failed: the earlier failure was about redundancy diluting useful columns, not about longer-range history being inherently unhelpful.

**Final production model (adopted) — Day1 R²=0.578, Day2 R²=0.232, Day3 R²=0.088.** `LAG_HOURS = [1, 3, 24, 48, 72]` in `src/config.py`; local feature cache (`aqi_features.csv`) regenerated from existing cached raw data (no API re-fetch needed, per Finding 7's confirmed gap-free history). Hopsworks feature store schema to be updated via a re-run of the backfill pipeline before final deployment, to keep the feature store as source of truth consistent with local development.

---

## Further Refinement — NASA FIRMS Fire/Hotspot Data (result: genuine improvement at Day 3, the target it was designed to help)

**Motivation:** Finding 1 identified post-harvest crop-residue burning as a driver of the winter AQI spike, but this was previously only represented indirectly via `month`. Added a direct measurement: daily aggregated fire/hotspot detections (NASA FIRMS VIIRS, Standard Processing, 2-year historical backfill via 5-day chunked API calls — the historical endpoint's max day-range, smaller than the weather archive's 90-day chunks) within a bounding box around the city, filtered to `type=0` (vegetation fires; 95% of raw detections, confirming the bounding box genuinely captures agricultural/vegetation burning rather than industrial heat sources).

**Features added:** `fire_count` (daily detection count) and `fire_frp_sum` (daily summed fire radiative power — an intensity measure, not just presence/absence). Distribution confirmed real, skewed seasonal signal (median 7 detections/day, 75th percentile 25, max 135) — consistent with a bursty, seasonal burning pattern rather than noise.

**Merge handling — important distinction from prior gap-handling:** days with zero fire detections are absent from the raw FIRMS response entirely (not represented as explicit zero rows). After a left-merge into the hourly feature table, these show up as `NaN` but represent a **confirmed zero**, not missing/unknown data — filled explicitly via `.fillna(0)` rather than dropped, unlike every other `NaN`-handling case in this project. Using `dropna()` here would have incorrectly discarded the majority of the dataset (most days, particularly during monsoon, legitimately have zero fire activity).

**Result — measured on the real held-out test set:**

| Horizon | Previous champion (48h/72h lags) | With fire data |
|---|---|---|
| Day 1 | 0.578 | 0.580 (~flat) |
| Day 2 | 0.232 | 0.224 (slightly down, within noise range observed elsewhere in this project) |
| Day 3 | **0.088** | **0.101** (+15% relative) |

**Why the gain concentrates at Day 3 specifically:** crop-residue burning's effect on air quality builds and persists over multiple days (smoke accumulation, regional transport) rather than appearing/dissipating within hours — consistent with fire data adding the most value at the longest forecast horizon, where Day 1 was already dominated by immediate lag/persistence signal with little room for a slower-moving feature to add further value.

**Final production model (adopted) — Day1 R²=0.580, Day2 R²=0.224, Day3 R²=0.101.** This represents the cumulative result of the full Phase 6 model-improvement effort: baseline (naive persistence) → Ridge → Random Forest → XGBoost (absolute target) → XGBoost (delta/residual target) → hyperparameter refinement (subsample=1.0) → extended lag windows (48h/72h) → NASA FIRMS fire data integration. Day 3 R² improved from -0.272 (naive baseline) to 0.101 across the full project — a meaningful, well-documented progression grounded in EDA findings at each step, not an arbitrary sequence of trial and error.

---

## Note on Metric Stability Across Backfill Runs

The production backfill pipeline anchors its 2-year window to the date of execution (`date.today()`), rather than a fixed historical range. Re-running the backfill at a later date shifts which specific calendar weeks fall into the chronological test split, causing reported metrics to drift somewhat between runs — observed directly: the champion's Day1/2/3 R² shifted from 0.580/0.224/0.101 to 0.586/0.221/0.073 after a later backfill re-run, using identical code. This is an expected property of a live, rolling forecasting system, not a modeling regression — reported metrics reflect the specific evaluation window at backfill time, and will naturally shift as new data accumulates. Final report figures should be generated from one backfill run close to submission, with this caveat stated explicitly.

## Experiment — Fire Temporal Features (lag/rolling/interaction terms) — result: negative, reverted

Extending the base fire features with a 24h lag, 7-day rolling mean, and a fire×low-wind interaction term was tested as a further refinement on the hypothesis that smoke persistence and dispersion conditions matter, not just same-day fire activity. Result was net negative (Day1 and Day2 measurably worse; Day3 essentially unchanged, within noise) — the same column-dilution mechanism identified in the Round 2 feature engineering and weather oracle experiments. Reverted; only the base `fire_count`/`fire_frp_sum` features (confirmed beneficial) were retained in the final model.

## Experiment — LightGBM Comparison — result: no meaningful difference, XGBoost retained

Trained an equivalent LightGBM model as a final check before formally closing the model-improvement search — same delta target, same `subsample=1.0`/`colsample_bytree=0.8` configuration, same early-stopping discipline as the XGBoost champion. Result: Day1 +0.008, Day2 -0.009, Day3 -0.005 relative to XGBoost — differences within the noise range already observed across this project's backfill reruns, not a decisive win either way. XGBoost retained per the project's established tiebreak rule (prefer the simpler/already-established option when a swap does not clearly win overall).

## Phase 6 — Formally Concluded

**Final model:** XGBoost, delta/residual target (`target_delta_dayH = target_aqi_dayH - us_aqi`, reconstructed at inference as `us_aqi + predicted_delta`), hyperparameters `subsample=1.0`, `colsample_bytree=0.8`, `learning_rate=0.05`, `max_depth=5`, `early_stopping_rounds=20`. Features: full engineered set including `LAG_HOURS=[1,3,24,48,72]` and NASA FIRMS fire data (`fire_count`, `fire_frp_sum`). Reported performance: Day1 R²≈0.58, Day2 R²≈0.22, Day3 R²≈0.07–0.10 (see metric stability note above).

**Next phases:** Model Registry, SHAP explainability, GitHub Actions automation (Phase 7), Streamlit dashboard (Phase 8), final written report.

---

## SHAP Explainability Analysis

**Method:** `shap.TreeExplainer` applied to each of the three per-horizon XGBoost delta models on the held-out test set. Unlike gain-based `feature_importances_` (a single magnitude per feature, aggregated globally), SHAP provides per-prediction, directional attributions — showing not just *that* a feature matters, but *which direction* it pushes each individual prediction, and for which specific rows.

**Finding — mean-reversion mechanism directly confirmed, with direction.** `us_aqi`/`aqi_lag_1h`/`aqi_lag_3h` show a consistent pattern across all three horizons: high current AQI pushes the predicted delta negative (model expects AQI to fall), low current AQI pushes it positive (model expects AQI to rise). This is the first direct, per-prediction confirmation of the mean-reversion mechanism inferred earlier from the Baseline Model Results (naive persistence degrading sharply at longer horizons).

**Finding — pressure/inversion mechanism confirmed with direction, at all three horizons.** `surface_pressure` shows the same pattern in every horizon: high pressure pushes the predicted delta positive (AQI expected to worsen), low pressure pushes it negative (AQI expected to improve). A direct, three-times-repeated confirmation of the inversion mechanism established in Finding 1/6 — now one of the most robustly evidenced findings in the project.

**Finding — short lags and long lags carry opposite directional signals (novel, not visible in prior feature-importance analysis).** Short-range lags (`aqi_lag_1h/3h`, `us_aqi`) show mean-reversion (high value → negative delta), while long-range lags (`aqi_lag_48h/72h`) show the *opposite* — high value → positive delta, an effect that strengthens at Day 3 (`aqi_lag_72h`'s SHAP values extend past +20). Interpretation: recent AQI spikes tend to be transient and mean-revert, but AQI that has remained elevated for 2–3 days looks more like a sustained pollution episode (e.g. a persistent inversion or extended burning period) likely to continue — a genuine trend-continuation signal, distinct from short-term mean-reversion. This directly explains why extending the lag window (48h/72h) produced a real, non-redundant improvement rather than just adding noise.

**Finding — `aqi_change_rate_1h` explained as a momentum signal, distinct from and complementary to the level-based mean-reversion signal.** Resolves the earlier open question (this feature's surprisingly high importance in the delta model despite negligible importance in the absolute-target model): AQI currently rising (positive change rate) pushes the predicted delta further positive; AQI currently falling pushes it negative — a short-term momentum effect operating alongside, not instead of, the mean-reversion mechanism carried by the lag/level features.

**Finding — temperature confirms the seasonal mechanism with direction (Day 3).** Cold temperatures push the predicted delta positive (worsening), warm temperatures push it negative (improving) — directly consistent with the winter-inversion/monsoon-dispersion mechanism from Finding 1, now confirmed directionally rather than only via correlation.

**Noted limitations, stated honestly rather than over-interpreted:** `pm2_5` shows a less clean, more mixed directional pattern (both high and low values appear on both sides of zero), suggesting its effect depends on interaction with other features rather than a single consistent direction. `month`'s directional pattern is difficult to interpret cleanly due to its raw-integer (non-cyclical) encoding — consistent with the earlier finding that cyclical encoding did not improve model performance (Round 2 Feature Engineering), but limiting how confidently direction can be read from this feature specifically.