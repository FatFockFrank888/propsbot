# MODERN QUANTITATIVE BETTING SPECIFICATION (`propsbot` — 2026)

> Inklistrad av användaren 2026-11-26 (filen fanns inte i repot). Granskning och plan: `docs/PLAN.md`.
> Obs: NHL togs bort 12/11; NBA saknas i specen men är vår största volym (se PLAN.md §2).

## 1. CORE ARCHITECTURE: MARKET-ANCHORED RESIDUAL MODEL + DISCRETE PROPS
Instead of training a standalone black-box classifier from scratch or relying only on static parametric formulas, implement a **Market-Anchored Residual Architecture**:

1. **No-Vig Market Baseline (`p_market`):**
   - Convert two-way prop odds `(O_over, O_under)` to fair probabilities using the **Power Method** (solves `(1/O_over)^k + (1/O_under)^k = 1`).
   - Convert to logit baseline: `base_logit = logit(clip(p_market, 1e-4, 1 - 1e-4))`.

2. **Residual Gradient Boosted Model (LightGBM Regressor / Binary Classifier with `init_score`):**
   - Pass `base_logit` as `init_score` during training and inference.
   - The model learns **corrections (`delta_logit`)** to the market's implied probability based on domain features that retail/prop markets often price sluggishly:
     - **Football Corners:** Team & opponent EWMA corners for/against, shots/blocked shots/crosses ratio, implied goal line & win probabilities (expected game-script / trailing-team push), home/away split, recent fixture congestion.
     - **Football Player Props:** Projected minutes / starter status, per-90 rate shrunk via Empirical Bayes toward positional prior, opponent concession rate to position/role, team implied goals, referee card/foul tendency.
     - **NHL Player Props:** Projected TOI (5v5 + PP), individual shot/point rates per 60, opponent shot/save/penalty rates, back-to-back / schedule density flags, home/away & empty-net context.

3. **Discrete Distribution & Calibration Layer:**
   - Where event counts or lines are modeled via expected count `lambda_hat`, compute `P(Y > line)` using **Negative Binomial** (`nbinom` with overdispersion parameter `alpha` estimated from historical residuals) rather than Gaussian approximations.
   - Apply **Isotonic Regression** (fitted strictly on out-of-sample walk-forward folds, never in-sample) to produce `p_calibrated`.

4. **Strict Anti-Leakage & Validation:**
   - Use **expanding/rolling walk-forward splits** ordered by match/event timestamp (`train_end < val_start < test_start`).
   - Primary selection metrics: **Log-Loss** and **CLV (Closing Line Value)** — never raw hit-rate or accuracy alone.

5. **Staking & Risk Guards:**
   - Compute `EV = p_calibrated * decimal_odds - 1`.
   - Filter by minimum EV threshold (e.g., `>= 0.035` for liquid markets, `>= 0.06` for high-variance/niche markets) and sanity-check extreme outliers (`p_calibrated - p_market <= 0.12` unless verified lineup/injury news).
   - Size bets with **Quarter-Kelly (`0.25 * kelly_fraction`)**, capped at a hard per-bet max (e.g., `2%–2.5%` of bankroll) and per-match cap when multiple props share the same game.

## 2. CLAUDE CODE INSTRUCTIONS
1. Inspect the existing `propsbot` codebase and data schema first.
2. Map available features from our current data sources/Google Sheets and list any missing features as optional (`NaN`-safe, since LightGBM handles missing values natively).
3. Propose a clean, modular Python structure (`features/`, `models/residual_model.py`, `pricing/devig.py`, `calibration/`, `staking/kelly.py`, `backtest/walk_forward.py`) with unit tests for:
   - Power de-vigging summing to `1.0`
   - Zero data leakage across chronological splits
   - Kelly stake caps and zero/negative EV returning `0.0` stake.
