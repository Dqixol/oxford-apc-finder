"""Runs client.py's extract_page() once per page in a journal's page
manifest (page_manifests.py), against one already-loaded vLLM server, then
merges the per-page JournalRecords into one whole-journal record.

Why this exists: a journal's guidance is usually spread across several pages
(the whole reason SourcedValue/ArticleType.source_url exist in schema.py --
see its docstring), but client.py's extract_page() only ever sees one page's
text per call, the same way the real Nature ground truth
(data_scrapes/1476-4687_nature/latest.json) was assembled from 8 separate
page reads, not one. Looping inside one Python process (rather than
resubmitting a SLURM job per page) matters because loading a 70B model takes
~20 minutes -- 8 pages as 8 separate run_extract.sh submissions would mean
~2.5 hours of pure model-loading before any real work happens.

Usage (see run_extract.sh, which now calls this by default when only SLUG
is given -- pass PAGE too on top of that for the old single-page behavior):
    python extract_journal.py --slug 1476-4687_nature \\
        --base-url http://localhost:8000/v1 --model Qwen/Qwen2.5-72B-Instruct-AWQ

Each page still gets its own `<date>.llm.<page>.json` / `.audit.json` (so
you can diff any one page's output against its own slice of latest.json, as
llm_extract/README.md's "Suggested first validation" section describes for
formatting-guide specifically) -- this just additionally writes one merged
`<date>.llm.full.json` covering the whole journal, comparable field-for-field
against the whole of latest.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import DATA_SCRAPES_DIR, check_vllm, extract_page  # noqa: E402
from page_manifests import pages_for_slug  # noqa: E402


def merge_records(slug: str, journal_name: str, issn_hint: str, page_records: list[tuple[str, dict]]) -> dict:
    """Combines one JournalRecord dict per page into a single whole-journal
    record. Simple, auditable rules rather than anything clever -- this is
    meant to be spot-checked against latest.json, not trusted blindly:

    - Top-level SourcedValue fields (peer_review_model, preprint_policy,
      ai_use_policy, latex_accepted, template_provided, robots_txt_allowed):
      first non-null value wins, in manifest page order. Each page's
      extraction was only ever looking at its own text, so if two pages both
      came back non-null for the same field that's worth a second look, not
      silently dropped -- both are kept as remarks (see collision handling
      below), not merged into one.
    - article_types: concatenated across pages, keyed by `type` name --
      first occurrence of a given type name wins; a repeat is noted, not
      overwritten (matches every ArticleType already carrying its own
      source_url, so which page it came from is traceable regardless).
    - needs_review: union of every page's needs_review, minus any field that
      ended up resolved (non-null) by a different page's record.
    - remarks: each page's own remarks kept, prefixed with which page it
      came from, plus any field-level collision notes.
    - languages_accepted: union, order-preserving.
    - journal / issn / url / date_scraped / source: journal-level identity,
      not sourced from any one page -- passed in by the caller, not read out
      of any per-page record.
    """
    today = date.today().isoformat()
    merged: dict = {
        "journal": journal_name,
        "publisher": None,
        "issn": {"print": None, "electronic": issn_hint},
        "url": None,  # set below, from the manifest's first page as the nominal landing page
        "date_scraped": today,
        "robots_txt_allowed": None,
        "peer_review_model": None,
        "preprint_policy": None,
        "ai_use_policy": None,
        "latex_accepted": None,
        "template_provided": None,
        "template_url": None,
        "languages_accepted": [],
        "article_types": [],
        "remarks": None,
        "needs_review": [],
        "source": "scraped",
    }

    sourced_fields = [
        "publisher", "robots_txt_allowed", "peer_review_model", "preprint_policy",
        "ai_use_policy", "latex_accepted", "template_provided", "template_url",
    ]
    remarks_parts: list[str] = []
    needs_review: set[str] = set()
    seen_article_types: dict[str, str] = {}  # type name -> which page it came from

    for i, (page, record) in enumerate(page_records):
        if i == 0:
            merged["url"] = record.get("url")

        for field in sourced_fields:
            val = record.get(field)
            if val is None:
                continue
            current = merged.get(field)
            if current is None:
                merged[field] = val
            elif current != val:
                remarks_parts.append(
                    f"[{page}] also gave a value for `{field}` that differs from an earlier "
                    f"page's -- kept the earlier one, this page's was: {json.dumps(val, ensure_ascii=False)}"
                )

        for lang in record.get("languages_accepted") or []:
            if lang not in merged["languages_accepted"]:
                merged["languages_accepted"].append(lang)

        for at in record.get("article_types") or []:
            name = at.get("type", "?")
            # Case/whitespace-insensitive only -- NOT fuzzy. Deliberately doesn't try to catch
            # "Registered Report" vs "Registered Reports" or "Article" vs "Research Article":
            # collapsing those automatically risks silently merging two things that are
            # genuinely different, which is worse than the inflated count this is meant to fix.
            # Real near-duplicates from inconsistent model naming across independent per-page
            # calls still show up as separate entries with a remarks collision note (see the
            # else branch) -- that's a prompt-consistency problem, not something safe to paper
            # over here.
            dedup_key = " ".join(name.split()).lower()
            if dedup_key in seen_article_types:
                remarks_parts.append(
                    f"[{page}] also produced an article type named '{name}', already supplied by "
                    f"[{seen_article_types[dedup_key]}] -- kept the earlier one; check both pages by hand "
                    f"if they might describe genuinely different things under the same name."
                )
                continue
            seen_article_types[dedup_key] = page
            merged["article_types"].append(at)

        if record.get("remarks"):
            remarks_parts.append(f"[{page}] {record['remarks']}")

        for path in record.get("needs_review") or []:
            needs_review.add(f"[{page}] {path}")

    resolved_top_level = {f for f in sourced_fields if merged.get(f) is not None}
    needs_review = {
        nr for nr in needs_review
        if not any(nr.endswith(f"] {f}") and f in resolved_top_level for f in sourced_fields)
    }

    merged["remarks"] = " | ".join(remarks_parts) if remarks_parts else None
    merged["needs_review"] = sorted(needs_review)
    return merged


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="e.g. 1476-4687_nature -- must have an entry in page_manifests.py")
    ap.add_argument("--journal-name", default=None, help="defaults to the slug's second half if omitted")
    ap.add_argument("--base-url", required=True, help="your vLLM OpenAI-compatible endpoint, e.g. http://host:8000/v1")
    ap.add_argument("--model", required=True, help="the model name as vLLM is serving it, e.g. Qwen/Qwen2.5-72B-Instruct-AWQ")
    ap.add_argument("--pages", default=None, help="comma-separated subset of page names to run (default: every page in the manifest)")
    ap.add_argument("--use-inline-schema", action="store_true")
    ap.add_argument("--skip-vllm-check", action="store_true")
    args = ap.parse_args()

    from openai import OpenAI

    if not args.skip_vllm_check:
        check_vllm(args.base_url, args.model)

    client = OpenAI(base_url=args.base_url, api_key="EMPTY")

    manifest = pages_for_slug(args.slug)
    if args.pages:
        wanted = set(args.pages.split(","))
        manifest = [(p, u) for p, u in manifest if p in wanted]
        missing = wanted - {p for p, _ in manifest}
        if missing:
            raise SystemExit(f"--pages named {sorted(missing)}, not present in the manifest for {args.slug!r}")

    journal_name = args.journal_name or args.slug.split("_", 1)[1].replace("-", " ").title()
    issn_hint = args.slug.split("_", 1)[0]

    print(f"Running extraction for {journal_name} across {len(manifest)} page(s): {[p for p, _ in manifest]}")

    page_records: list[tuple[str, dict]] = []
    for page, source_url in manifest:
        print(f"\n--- {page} ({source_url}) ---")
        record, _report = extract_page(
            client, args.model,
            slug=args.slug, page=page, source_url=source_url, journal_name=journal_name,
            use_inline_schema=args.use_inline_schema, out_suffix=page,
        )
        page_records.append((page, record))

    merged = merge_records(args.slug, journal_name, issn_hint, page_records)

    out_dir = DATA_SCRAPES_DIR / args.slug
    today = date.today().isoformat()
    model_tag = args.model.rsplit("/", 1)[-1]  # see client.extract_page()'s comment: model MUST be in the filename
    merged_path = out_dir / f"{today}.llm.{model_tag}.full.json"
    merged_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWrote merged whole-journal record: {merged_path}")
    print(f"  article_types: {[at.get('type') for at in merged['article_types']]}")
    print(f"  needs_review: {merged['needs_review']}")
    if merged["remarks"]:
        print(f"  remarks: {merged['remarks']}")


if __name__ == "__main__":
    main()
