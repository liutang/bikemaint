# Research: 085 Blended Riding Pace

## 1. Why the blend

- **Decision**: the mean of the 90-day and whole-history paces.
- **Rationale**: a backtest on the rider's data, 21 forecasts over 13 completed chain cycles, gave these typical misses:

  | Method | All | Steady riding |
  |---|---|---|
  | Blend | 18 days | 5 days |
  | 90-day | 22–27 days | 11–12 days |
  | Weighted average | 28–29 days | 5 days |
  | Whole history | 17 days | 11 days |
  | Past year | 30–50 days | 19–30 days |
  | Trend-switching rules | 25–44 days | 5–6 days |

  The blend is the only method near the best in both columns.
- **Alternatives considered**:
  - The weighted average: best when riding is steady, poor when it changes.
  - Trend switching: no better than the blend, and at risk of fitting the rider's past.
  - The part's own riding: worse in every column, because a chain's installed history is short and broken up.

## 2. Confidence

- **Decision**: trusted when the bike has at least 5 counted rides and at least 30 days of history (rider-chosen).
- **Rationale**: the old rule flagged every quiet season, even though the blend still has years of history to draw on.

## 3. Hours

- **Decision**: the whole-history hours pace starts at the bike's first ride with a moving time (rider-confirmed).
- **Rationale**: rides from before moving time was recorded would otherwise count as 0 hours.
