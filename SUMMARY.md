# Bastion Telemetry — Daily Sanitized Feed

**Last updated:** 2026-07-02
**Date range:** 2026-06-18 to 2026-07-02
**Total sanitized records:** ~1.2M signal events, ~180K execution events

## Structure

```
by_date/YYYY-MM-DD/
  signals.jsonl        — Signal tape (BLOCKED, CANDIDATE, PASSED, EXECUTED)
  execution.jsonl      — Execution ledger (regime observations, fills)
  logs/                — Pipeline/retrain logs (if available)
  certification/       — Live certification reports (if available)
  trade_history/       — FTMO trade history (ticket IDs hashed)
  audit/               — Bastion audit reports (if available)

aggregated/
  signals_all.jsonl    — Concatenated signal tape (all dates)
  execution_all.jsonl  — Concatenated execution ledger (all dates)

schemas/
  signal_tape.schema.json
  execution_ledger.schema.json

scripts/
  sanitise.py          — Sanitisation engine
  rules.yaml           — Redaction/hashing rules
```

## What's Sanitized

- Absolute paths → `<REDACTED_PATH>`
- Username/hostname → `<USER>` / `<HOST>`
- Config/manifest hashes → `<HASH>`
- Event IDs → 16-char SHA hash
- Ticket IDs → 16-char SHA hash
- Emails → `<EMAIL>`
- LinkedIn URLs → `<LINKEDIN_URL>`

## What's NOT Included

- Live open positions or exact SL/TP prices
- Model weights, thresholds, or feature schemas
- Real-time signal timing (24-hour delay enforced)
- Specific position sizes in lots (only % risk shown)

## Data Quality Notes

| Date | signals.jsonl | execution.jsonl | Notes |
|------|--------------|-----------------|-------|
| 2026-06-18 | 10.6 MB | 8.2 MB | — |
| 2026-06-19 | 16.9 MB | 13.4 MB | — |
| 2026-06-22 | 7.0 MB | 5.5 MB | — |
| 2026-06-23 | 37.6 MB | 29.8 MB | — |
| 2026-06-24 | 48.9 MB | 38.7 MB | — |
| 2026-06-25 | 47.0 MB | 37.2 MB | — |
| 2026-06-26 | 1.4 MB | 1.1 MB | — |
| 2026-06-28 | 1.7 MB | 1.3 MB | — |
| 2026-06-29 | 6.0 MB | 4.7 MB | — |
| 2026-06-30 | 34.7 MB | 27.5 MB | — |
| 2026-07-01 | 14.2 MB | 11.2 MB | — |
| 2026-07-02 | — | — | In progress |

---

*For methodology, see [Validation-Framework](https://github.com/BastionQuantitativeSolutions/Validation-Framework)*
