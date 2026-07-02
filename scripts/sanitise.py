#!/usr/bin/env python3
"""
Cavalier Telemetry Sanitiser
============================
Ingests raw telemetry from the Cavalier trading system, applies redaction/hashing/
removal rules, and writes sanitised output ready for external sharing (e.g. GitHub).

Usage:
    python sanitise.py [--dry-run] [--verbose] [--date YYYY-MM-DD]

Output structure:
    clean/by_date/YYYY-MM-DD/
        signals.jsonl
        execution.jsonl
        logs/
        certification/
        trade_history/
        audit/
    clean/aggregated/
        signals_all.jsonl        (concatenated)
        execution_all.jsonl      (concatenated)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
CAVALIER_ROOT = Path(r"C:\Users\jack\Cavalier")
TELEMETRY_ROOT = CAVALIER_ROOT / "telemetry_sanitised"
RULES_PATH = TELEMETRY_ROOT / "scripts" / "rules.yaml"


# ---------------------------------------------------------------------------
# Rule Engine
# ---------------------------------------------------------------------------
class Sanitiser:
    def __init__(self, rules_path: Path) -> None:
        with open(rules_path, "r", encoding="utf-8") as f:
            self.rules = yaml.safe_load(f)

        self.redactions = self.rules.get("redactions", [])
        self.hash_fields = self.rules.get("hash_fields", [])
        self.remove_keys = set(self.rules.get("remove_keys", []))
        self.remove_files = self.rules.get("remove_files", [])
        self.handlers = self.rules.get("file_type_handlers", {})

        # Compile regex patterns
        for r in self.redactions:
            r["_compiled"] = re.compile(r["pattern"])

        self.hash_field_names = {h["field"] for h in self.hash_fields}
        self.hash_config = {h["field"]: h for h in self.hash_fields}

    # ------------------------------------------------------------------
    # Core transforms
    # ------------------------------------------------------------------
    def redact_text(self, text: str) -> str:
        for rule in self.redactions:
            text = rule["_compiled"].sub(rule["replacement"], text)
        return text

    def hash_value(self, field: str, value: Any) -> Any:
        if value is None and self.hash_config.get(field, {}).get("null_passthrough", False):
            return None
        if value == "" and self.hash_config.get(field, {}).get("empty_passthrough", False):
            return ""
        if value is None or value == "":
            return value
        s = str(value).encode("utf-8")
        return hashlib.sha256(s).hexdigest()[:16]

    def sanitise_json_obj(self, obj: Any, field_name: str = "") -> Any:
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if k in self.remove_keys:
                    continue
                if k in self.hash_field_names:
                    out[k] = self.hash_value(k, v)
                else:
                    out[k] = self.sanitise_json_obj(v, field_name=k)
            return out
        if isinstance(obj, list):
            return [self.sanitise_json_obj(i, field_name=field_name) for i in obj]
        if isinstance(obj, str):
            # Special-case hash fields where the regex expects key:value context
            # but we only have the value after JSON parsing
            if field_name in ("config_hash", "model_manifest_hash") and re.fullmatch(r"[a-f0-9]{64}", obj):
                return "<HASH>"
            return self.redact_text(obj)
        return obj

    def should_skip_file(self, rel_path: str) -> bool:
        for pattern in self.remove_files:
            if fnmatch(rel_path, pattern) or fnmatch(rel_path.lower(), pattern.lower()):
                return True
        return False


# ---------------------------------------------------------------------------
# File Processors
# ---------------------------------------------------------------------------
class Ingestor:
    def __init__(self, sanitiser: Sanitiser, dry_run: bool = False, verbose: bool = False):
        self.san = sanitiser
        self.dry_run = dry_run
        self.verbose = verbose
        self.stats = {"files_read": 0, "files_written": 0, "lines_processed": 0, "bytes_in": 0, "bytes_out": 0}

    def log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def write_text(self, path: Path, content: str) -> None:
        if self.dry_run:
            self.log(f"[DRY-RUN] Would write {path} ({len(content)} chars)")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.stats["files_written"] += 1
        self.stats["bytes_out"] += len(content.encode("utf-8"))

    def write_bytes(self, path: Path, data: bytes) -> None:
        if self.dry_run:
            self.log(f"[DRY-RUN] Would write {path} ({len(data)} bytes)")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        self.stats["files_written"] += 1
        self.stats["bytes_out"] += len(data)

    # ------------------------------------------------------------------
    # JSONL
    # ------------------------------------------------------------------
    def process_jsonl(self, src: Path, dst: Path) -> None:
        self.log(f"Processing JSONL: {src}")
        out_lines = []
        with open(src, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    out_lines.append(self.san.redact_text(line))
                    continue
                obj = self.san.sanitise_json_obj(obj)
                out_lines.append(json.dumps(obj, ensure_ascii=False))
                self.stats["lines_processed"] += 1

        self.write_text(dst, "\n".join(out_lines) + "\n")
        self.stats["files_read"] += 1
        self.stats["bytes_in"] += src.stat().st_size

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------
    def process_json(self, src: Path, dst: Path) -> None:
        self.log(f"Processing JSON: {src}")
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
        data = self.san.sanitise_json_obj(data)
        self.write_text(dst, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        self.stats["files_read"] += 1
        self.stats["bytes_in"] += src.stat().st_size

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------
    def process_csv(self, src: Path, dst: Path) -> None:
        self.log(f"Processing CSV: {src}")
        out_lines = []
        with open(src, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            ticket_col_idx = None
            if header:
                # Detect ticket ID column
                for idx, h in enumerate(header):
                    if h.strip().lower() in ("ticket", "ticket_id", "order_id", "event_id"):
                        ticket_col_idx = idx
                        break
                out_lines.append(",".join(self.san.redact_text(h) for h in header))
            for row in reader:
                processed = []
                for idx, cell in enumerate(row):
                    if idx == ticket_col_idx and cell.strip():
                        processed.append(self.san.hash_value("ticket_id", cell))
                    else:
                        processed.append(self.san.redact_text(cell))
                out_lines.append(",".join(processed))
                self.stats["lines_processed"] += 1

        self.write_text(dst, "\n".join(out_lines) + "\n")
        self.stats["files_read"] += 1
        self.stats["bytes_in"] += src.stat().st_size

    # ------------------------------------------------------------------
    # Text / Logs / Markdown
    # ------------------------------------------------------------------
    def process_text(self, src: Path, dst: Path) -> None:
        self.log(f"Processing text: {src}")
        with open(src, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        text = self.san.redact_text(text)
        self.write_text(dst, text)
        self.stats["files_read"] += 1
        self.stats["bytes_in"] += src.stat().st_size

    # ------------------------------------------------------------------
    # Auto-detect by extension
    # ------------------------------------------------------------------
    def process_auto(self, src: Path, dst: Path) -> None:
        ext = src.suffix.lower()
        if ext == ".jsonl":
            self.process_jsonl(src, dst)
        elif ext == ".json":
            self.process_json(src, dst)
        elif ext == ".csv":
            self.process_csv(src, dst)
        else:
            self.process_text(src, dst)

    # ------------------------------------------------------------------
    # Directory scanning
    # ------------------------------------------------------------------
    def find_sources(self, pattern: str, root: Path) -> list[Path]:
        results = []
        if "**" in pattern:
            # recursive glob
            parts = pattern.split("/")
            if parts[0] == "**":
                # /**/filename
                fname = parts[-1]
                for p in root.rglob(fname):
                    results.append(p)
            else:
                base = root / parts[0]
                rest = "/".join(parts[1:])
                for p in base.rglob(rest.replace("**", "").lstrip("/")):
                    results.append(p)
        else:
            # simple relative glob
            for p in root.rglob(pattern):
                results.append(p)
        return sorted(results)

    def extract_date_from_path(self, p: Path) -> str | None:
        """Try to extract YYYY-MM-DD from path."""
        # artifacts/20260630/telemetry/...  → 2026-06-30
        for part in p.parts:
            if len(part) == 8 and part.isdigit():
                try:
                    dt = datetime.strptime(part, "%Y%m%d")
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass
            # Also handle date=2026-06-28 patterns
            if part.startswith("date="):
                try:
                    dt = datetime.strptime(part[5:15], "%Y-%m-%d")
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass
        # Fallback: file mtime
        mtime = datetime.fromtimestamp(p.stat().st_mtime)
        return mtime.strftime("%Y-%m-%d")

    # ------------------------------------------------------------------
    # Main entry: run full sanitisation
    # ------------------------------------------------------------------
    def run(self, target_date: str | None = None) -> None:
        print(f"{'='*60}")
        print("Cavalier Telemetry Sanitiser")
        print(f"Cavalier root: {CAVALIER_ROOT}")
        print(f"Output root:   {TELEMETRY_ROOT / 'clean'}")
        print(f"Dry run:       {self.dry_run}")
        print(f"{'='*60}\n")

        # --- 1. Signal tape ------------------------------------------------
        sig_handler = self.san.handlers.get("signal_tape", {})
        sig_sources = self.find_sources(sig_handler.get("source_pattern", "**/signal_tape.jsonl"), CAVALIER_ROOT)
        for src in sig_sources:
            rel = src.relative_to(CAVALIER_ROOT).as_posix()
            if self.san.should_skip_file(rel):
                self.log(f"Skipping (rule): {rel}")
                continue
            date = self.extract_date_from_path(src)
            if target_date and date != target_date:
                continue
            dst = TELEMETRY_ROOT / "clean" / "by_date" / date / "signals.jsonl"
            self.process_jsonl(src, dst)

        # --- 2. Execution ledger -------------------------------------------
        exec_handler = self.san.handlers.get("execution_ledger", {})
        exec_sources = self.find_sources(exec_handler.get("source_pattern", "**/execution_ledger.jsonl"), CAVALIER_ROOT)
        for src in exec_sources:
            rel = src.relative_to(CAVALIER_ROOT).as_posix()
            if self.san.should_skip_file(rel):
                continue
            date = self.extract_date_from_path(src)
            if target_date and date != target_date:
                continue
            dst = TELEMETRY_ROOT / "clean" / "by_date" / date / "execution.jsonl"
            self.process_jsonl(src, dst)

        # --- 3. Logs -------------------------------------------------------
        log_handler = self.san.handlers.get("logs", {})
        log_sources = self.find_sources(log_handler.get("source_pattern", "**/*.log"), CAVALIER_ROOT)
        for src in log_sources:
            rel = src.relative_to(CAVALIER_ROOT).as_posix()
            if self.san.should_skip_file(rel):
                continue
            date = self.extract_date_from_path(src)
            if target_date and date != target_date:
                continue
            basename = src.name
            dst = TELEMETRY_ROOT / "clean" / "by_date" / date / "logs" / basename
            self.process_text(src, dst)

        # --- 4. Certification reports --------------------------------------
        cert_json_handler = self.san.handlers.get("certification_json", {})
        cert_json_sources = self.find_sources(cert_json_handler.get("source_pattern", "**/live_certification_report.json"), CAVALIER_ROOT)
        for src in cert_json_sources:
            rel = src.relative_to(CAVALIER_ROOT).as_posix()
            if self.san.should_skip_file(rel):
                continue
            date = self.extract_date_from_path(src)
            if target_date and date != target_date:
                continue
            dst = TELEMETRY_ROOT / "clean" / "by_date" / date / "certification" / f"{date}_certification.json"
            self.process_json(src, dst)

        cert_md_handler = self.san.handlers.get("certification_md", {})
        cert_md_sources = self.find_sources(cert_md_handler.get("source_pattern", "**/live_certification_report.md"), CAVALIER_ROOT)
        for src in cert_md_sources:
            rel = src.relative_to(CAVALIER_ROOT).as_posix()
            if self.san.should_skip_file(rel):
                continue
            date = self.extract_date_from_path(src)
            if target_date and date != target_date:
                continue
            dst = TELEMETRY_ROOT / "clean" / "by_date" / date / "certification" / f"{date}_certification.md"
            self.process_text(src, dst)

        # --- 5. Trade history ----------------------------------------------
        trade_handler = self.san.handlers.get("trade_history", {})
        trade_sources = self.find_sources(trade_handler.get("source_pattern", "**/ftmo_trade_history*.csv"), CAVALIER_ROOT)
        for src in trade_sources:
            rel = src.relative_to(CAVALIER_ROOT).as_posix()
            if self.san.should_skip_file(rel):
                continue
            date = self.extract_date_from_path(src)
            if target_date and date != target_date:
                continue
            dst = TELEMETRY_ROOT / "clean" / "by_date" / date / "trade_history" / src.name
            self.process_csv(src, dst)

        # --- 6. Audit reports ----------------------------------------------
        audit_handler = self.san.handlers.get("audit_reports", {})
        audit_sources = self.find_sources(audit_handler.get("source_pattern", "bastion_audit/reports/*"), CAVALIER_ROOT)
        for src in audit_sources:
            rel = src.relative_to(CAVALIER_ROOT).as_posix()
            if self.san.should_skip_file(rel):
                continue
            date = self.extract_date_from_path(src)
            if target_date and date != target_date:
                continue
            dst = TELEMETRY_ROOT / "clean" / "by_date" / date / "audit" / src.name
            self.process_auto(src, dst)

        # --- 7. Build aggregated files -------------------------------------
        if not self.dry_run and not target_date:
            self._build_aggregates()

        # --- Stats ---------------------------------------------------------
        print(f"\n{'='*60}")
        print("Done. Stats:")
        for k, v in self.stats.items():
            print(f"  {k}: {v}")
        print(f"{'='*60}")

    def _build_aggregates(self) -> None:
        """Concatenate all by_date signals and execution into single files."""
        clean_root = TELEMETRY_ROOT / "clean"
        by_date = clean_root / "by_date"
        agg = clean_root / "aggregated"
        agg.mkdir(parents=True, exist_ok=True)

        for fname in ("signals.jsonl", "execution.jsonl"):
            out_path = agg / fname.replace(".jsonl", "_all.jsonl")
            with open(out_path, "w", encoding="utf-8") as out_f:
                for date_dir in sorted(by_date.iterdir()):
                    src = date_dir / fname
                    if src.exists():
                        with open(src, "r", encoding="utf-8") as in_f:
                            out_f.write(in_f.read())
            self.log(f"Built aggregate: {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Cavalier Telemetry Sanitiser")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--date", type=str, default=None, help="Only process a specific date (YYYY-MM-DD)")
    parser.add_argument("--rules", type=Path, default=RULES_PATH, help="Path to rules YAML")
    args = parser.parse_args()

    if not args.rules.exists():
        print(f"Rules file not found: {args.rules}", file=sys.stderr)
        return 1

    sanitiser = Sanitiser(args.rules)
    ingestor = Ingestor(sanitiser, dry_run=args.dry_run, verbose=args.verbose)
    ingestor.run(target_date=args.date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
