# FOOTBALL PLAYER PROPS SPECIFICATION (`propsbot` — 2026)

> Inklistrad av användaren 2026-11-26. Granskning och plan: `docs/PLAN_FOOTBALL_PROPS.md`.

## 1. TARGET MARKETS
- **Shot Markets:** Player Shots (`0.5+`, `1.5+`, `2.5+`), Player Shots on Target / SOT (`0.5+`, `1.5+`).
- **Action / Defensive Markets:** Player Tackles (`1.5+`, `2.5+`), Player Fouls Committed (`0.5+`, `1.5+`), Player To Be Booked / Cards (`0.5+`).

## 2. MATHEMATICAL & ML PIPELINE (MARKET-ANCHORED HYBRID)

### Step A: No-Vig Market Baseline (`pricing/devig.py`)
- Extract fair market probability `p_market` from two-way Over/Under odds using the **Power Method** (`(1/O_over)^k + (1/O_under)^k = 1`).
- For one-way markets (e.g., "To Be Booked" without an explicit Under line), estimate vig using league-average hold (`~7–9%` for retail books) or sharp benchmark odds when available.
- Convert to baseline log-odds: `base_logit = logit(clip(p_market, 1e-4, 1 - 1e-4))`.

### Step B: Minutes & Lineup Gate (`features/minutes.py`)
- **Hard Rule:** Never price a player prop at full strength without knowing whether the player is starting.
- **Lineup Status Handling:**
  - `CONFIRMED_XI`: Use player's historical expected minutes when starting (`E[mins | start]`, typically `72–90` mins depending on substitution tendency and fixture congestion).
  - `PROJECTED_XI` (pre-lineup): Multiply expected minutes by `P(starts)` and flag signal as `PRE_LINEUP` (require higher EV threshold).
  - `BENCH / DOUBTFUL`: Suppress bet automatically (`stake = 0.0`).

### Step C: Empirical Bayes Shrinkage & Per-90 Rates (`features/player_rates.py`)
- Raw per-90 rates on small samples (`< 500` minutes) are noisy. Compute shrunk per-90 baseline rate for every stat:
  $$\hat{\mu}_{90} = \frac{M_{\text{player}} \cdot \bar{x}_{90,\text{player}} + M_{\text{prior}} \cdot \mu_{90,\text{pos\_league}}}{M_{\text{player}} + M_{\text{prior}}}$$
  - $M_{\text{player}}$ = weighted minutes played (exponentially decayed, half-life ~12–15 matches, plus previous season prior at 30% weight).
  - $M_{\text{prior}}$ = shrinkage constant in minutes (e.g., `450` for Shots/Tackles/Fouls; `630` for SOT/Cards).
  - $\mu_{90,\text{pos\_league}}$ = positional average per 90 in that league and role (`CB`, `FB/WB`, `DM/CM`, `AM/W`, `ST`).
- Scale: $\lambda_{\text{base}} = \hat{\mu}_{90} \cdot \hat{M}_{\text{expected}} / 90$

### Step D: Contextual & Tactical Features (`features/match_context.py`)
1. **Game Script / Team Implied Strength:** win probability, implied team goals, spread from 1X2 / AH / Team Total. Heavy favorites (`implied_goals > 2.0`) inflate forward Shots/SOT and deflate CB/DM Tackles; heavy underdogs inflate Tackles/Fouls/Cards and suppress forward Shots.
2. **Opponent Positional Concession (`opp_allowed_factor`):** opponent's conceded events per 90 to that position group / league average.
3. **Set-Piece & Penalty Duty Flags:** penalty taker, direct free-kick taker, corner taker.
4. **Referee Strictness Factor (Fouls & Cards only):** `ref_cards_per_foul`, `ref_fouls_per_match` vs league mean (`> 1.15` boosts).
5. **Home/Away & Rest Days:** home multiplier + short-rest flag (`<= 3 days`).

### Step E: Discrete Distribution + LightGBM Residual Model (`models/football_props.py`)
- **Parametric Count Anchor:** `p_count = 1 - nbinom.cdf(floor(line), n=kappa, p=kappa/(kappa+lambda_adjusted))`, `kappa` fitted per stat type.
- **ML Residual Layer:** `LGBMClassifier(objective='binary')` with `init_score = base_logit`. Features: `logit(p_count) - base_logit`, `expected_minutes`, `lineup_confirmed`, `lambda_team_goals`, `opp_allowed_factor`, `ref_strictness`, `is_home`, `rest_days`, `set_piece_flag`, `sample_minutes`. Output `p_raw = sigmoid(base_logit + delta_logit)`.
- **Calibration:** `IsotonicRegression(out_of_bounds='clip')` strictly on out-of-sample walk-forward folds → `p_calibrated`.

## 3. BET SELECTION, RISK FILTERS & STAKING (`staking/kelly.py`)
- `ev = p_calibrated * decimal_odds - 1.0`.
- Thresholds: Confirmed XI + Shots/SOT `ev >= 0.04`; Confirmed XI + Tackles/Fouls/Cards `ev >= 0.06`; `PROJECTED_XI` +0.025 and half Kelly.
- Stale-line guard: `p_calibrated - p_market > 0.14` → `MANUAL_REVIEW / POSSIBLE_INJURY_OR_STALE_LINE`.
- Quarter-Kelly `0.25 * (p*o - 1)/(o - 1)`, cap 2.0 % per bet.
- Same player: only the single highest-EV prop per player per match. Same team/match: subsequent stakes × 0.65, total match exposure ≤ 3.5 %.

## 4. IMPLEMENTATION DIRECTIVE
1. Plan Mode first; audit repo against this spec.
2. Check which fields (minutes, positions, lineups, referee, opponent stats, 2-way vs 1-way odds) exist and which need `NaN` fallbacks or proxies.
3. Produce `docs/PLAN_FOOTBALL_PROPS.md` with phased steps and unit tests for: power de-vig accuracy, EB shrinkage convergence (low vs high minutes), zero leakage in walk-forward splits, lineup suppression and same-player/same-match staking caps.
