# Public Telemetry Data Dictionary

All published telemetry is delayed and sanitized.

| Field | Meaning | Publication rule |
|---|---|---|
| `timestamp` | UTC event or snapshot time | delayed by policy |
| `component` | system component name | generic labels only |
| `status` | `OK`, `WARN`, `FAIL`, or equivalent | safe |
| `latency_ms` | component latency | rounded or bucketed |
| `regime` | public regime label | no thresholds |
| `expected_r` | delayed/sanitized expected return bucket | bucketed where needed |
| `actual_r` | delayed/sanitized realized R | no price reconstruction |
| `pnl_pct` | percent PnL | no lot size or balance path reconstruction |

Never publish account IDs, ticket IDs, live open positions, exact entry prices,
exact exits, stop loss, take profit, production feature vectors, or model weights.
