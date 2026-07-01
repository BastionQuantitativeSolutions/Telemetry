# Telemetry

**Bastion Quantitative Solutions — Public Telemetry Feed**

Daily sanitized telemetry from the Cavalier trading system. All data is delayed by **24 hours** to protect live edge while proving system consistency.

## What's Published

| File | Description |
|------|-------------|
| `YYYY/MM/DD/regime_snapshot.json` | 82-stem regime states (TRENDING, RANGING, VOLATILE) |
| `YYYY/MM/DD/expected_r_matrix.csv` | Expected return per stem |
| `YYYY/MM/DD/tail_risk_matrix.csv` | Tail risk per stem |
| `YYYY/MM/DD/signal_bias_summary.md` | LONG/SHORT/NEUTRAL bias summary |
| `YYYY/MM/DD/risk_governor_state.json` | Daily drawdown, heat, position count |
| `YYYY/MM/DD/closed_trades_sanitized.csv` | Yesterday's closed trades (no ticket IDs, no entry/exit prices) |
| `YYYY/MM/DD/p0_epoch_status.json` | Post-P0 validation update |

## What's NOT Published

- Live open positions or exact SL/TP prices
- Model weights, thresholds, or feature schemas
- Real-time signal timing (24-hour delay enforced)
- Specific position sizes in lots (only % risk shown)

## Closed Trades Format

```csv
date,symbol,timeframe,direction,hold_time_minutes,pnl_pct,regime,model_family,expected_r,actual_r,payoff_guard_fired
2026-06-29,EURUSD,M15,LONG,45,0.32,TRENDING,catboost,0.8,0.4,FALSE
```

## Automation

This repository is auto-updated daily at 00:05 UTC by a GitHub Action that:
1. Reads yesterday's telemetry from Cavalier
2. Sanitizes and formats the data
3. Commits to this repo

## Verification

You can verify our regime calls against your own data. Fork this repo and compare our regime snapshots against actual price action.

## Disclaimer

This is research-grade telemetry, not financial advice. Past performance does not guarantee future results. The 24-hour delay means this data is not actionable for live trading.

---

*For the validation framework, see [BastionQuantitativeSolutions/Validation-Framework](https://github.com/BastionQuantitativeSolutions/Validation-Framework)*
*For research tools, see [BastionQuantitativeSolutions/Research-Tools](https://github.com/BastionQuantitativeSolutions/Research-Tools)*
