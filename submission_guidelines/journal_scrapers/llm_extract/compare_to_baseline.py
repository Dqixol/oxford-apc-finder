"""Combines a journal's known-good baseline (latest.json) with one or more
LLM extraction runs (<date>.llm.<model_tag>.full.json, from extract_journal.py)
into a single Excel workbook, one row per (source, article type) -- so a
baseline row and each model's row for e.g. "Registered Report" sit next to
each other and can be read side by side.

Reuses common/json_to_excel.py's record_to_rows()/build_workbook() as-is --
this script's only job is picking which JSON files count as which source and
labeling them, not re-deriving the flattening logic that already exists.

Usage:
    python compare_to_baseline.py --slug 1476-4687_nature

Auto-discovers every data_scrapes/<slug>/*.llm.*.full.json (extract_journal.py's
merged output) and labels each by the model tag embedded in its filename.
Pass --baseline-label to change the baseline's label from the default
("Claude Code Agent baseline"), or --llm-label-prefix to change how each LLM
run's label is built (default: "LLM extraction: <model_tag> (self-hosted via
vLLM, HPC)").
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.json_to_excel import build_workbook  # noqa: E402

DATA_SCRAPES_DIR = Path(__file__).resolve().parents[2] / "data_scrapes"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="e.g. 1476-4687_nature")
    ap.add_argument("--baseline-label", default="Claude Code Agent baseline")
    ap.add_argument(
        "--llm-label-prefix", default="LLM extraction:",
        help="each auto-discovered LLM run is labeled '<prefix> <model_tag> (self-hosted via vLLM, HPC)'",
    )
    ap.add_argument(
        "--out", default=None,
        help="output .xlsx path (default: data_scrapes/<slug>/<slug>_baseline_vs_llm.xlsx)",
    )
    args = ap.parse_args()

    slug_dir = DATA_SCRAPES_DIR / args.slug
    records = []

    baseline_path = slug_dir / "latest.json"
    if baseline_path.exists():
        record = json.loads(baseline_path.read_text(encoding="utf-8"))
        record["source"] = args.baseline_label
        records.append(record)
        print(f"Baseline: {baseline_path} -> labeled {args.baseline_label!r}")
    else:
        print(f"No baseline found at {baseline_path} -- proceeding with LLM runs only.")

    llm_paths = sorted(slug_dir.glob("*.llm.*.full.json"))
    if not llm_paths:
        raise SystemExit(
            f"No <date>.llm.<model_tag>.full.json files found under {slug_dir} -- "
            f"has extract_journal.py been run for this slug?"
        )
    for path in llm_paths:
        # filename shape: <date>.llm.<model_tag>.full.json -- model_tag is everything
        # between "llm." and ".full.json", which is exactly what client.py/
        # extract_journal.py derive from --model (e.g. "Qwen2.5-72B-Instruct-AWQ").
        stem = path.name.removesuffix(".full.json")
        model_tag = stem.split(".llm.", 1)[1]
        record = json.loads(path.read_text(encoding="utf-8"))
        record["source"] = f"{args.llm_label_prefix} {model_tag} (self-hosted via vLLM, HPC)"
        records.append(record)
        print(f"LLM run: {path} -> labeled {record['source']!r}")

    wb = build_workbook(records)
    out_path = Path(args.out) if args.out else slug_dir / f"{args.slug}_baseline_vs_llm.xlsx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    print(f"\nWrote {out_path} ({len(records)} source(s), {sum(len(r.get('article_types') or [{}]) for r in records)} rows)")


if __name__ == "__main__":
    main()
