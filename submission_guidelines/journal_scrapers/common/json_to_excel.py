"""Flatten scraped journal JSON records into a single Excel workbook for easy review.

Reads every data_scrapes/<issn>_<slug>/latest.json and writes one row per
(journal, article type) to data_scrapes/journals_overview.xlsx. Nested fields
(required sections, section word limits, figure limits, needs_review) are
joined into single "; "-separated cells rather than spread across columns,
since the number of article types/sections/figure-limit entries varies per
journal. Any missing value is written as "NA" in the spreadsheet -- the
underlying JSON keeps proper `null`/`[]` so downstream code can still tell
"missing" apart from the literal string "NA".

Run directly: `python journal_scrapers/common/json_to_excel.py`
"""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

DATA_SCRAPES_DIR = Path(__file__).resolve().parents[2] / "data_scrapes"
OUTPUT_PATH = DATA_SCRAPES_DIR / "journals_overview.xlsx"

NA = "NA"

COLUMNS = [
    "Journal", "Publisher", "ISSN (print)", "ISSN (electronic)",
    "General URL (for-authors landing page)",
    "Date scraped", "Source",
    "Robots.txt allowed", "Robots.txt source", "Robots.txt notes",
    "Peer review model", "Peer review model source", "Peer review model notes",
    "Preprint policy", "Preprint policy source",
    "AI use policy", "AI use policy source",
    "LaTeX accepted", "LaTeX source", "LaTeX notes",
    "Template provided", "Template provided source", "Template provided notes",
    "Template URL (actual resource, if any)",
    "ORCID required", "ORCID required source", "ORCID required notes",
    "Languages accepted",
    "Article type", "Article type source", "Article type description", "Submission mode",
    "Total word limit (min)", "Total word limit (max)", "Total word limit (unit)",
    "Total word limit (excludes)", "Total word limit (notes)",
    "Required sections",
    "Figure limits",
    "Reference limit", "Reference style",
    "Author limit",
    "Required statements",
    "Article type notes",
    "Remarks", "Needs review",
]


def _na(value):
    """Blank/None/empty collection -> "NA"; everything else passed through as-is."""
    if value is None:
        return NA
    if isinstance(value, (list, tuple)) and not value:
        return NA
    if isinstance(value, str) and not value.strip():
        return NA
    return value


def _sourced(record: dict, key: str) -> tuple:
    """A SourcedValue field ({value, source_url, notes}) -> (value, source_url, notes) tuple."""
    d = record.get(key) or {}
    return d.get("value"), d.get("source_url"), d.get("notes")


def _join(items) -> str:
    return "; ".join(str(i) for i in items) if items else ""


def _required_sections_str(article_type: dict) -> str:
    """Sections list, with each section's word limit appended in brackets where known."""
    sections = article_type.get("required_sections") or []
    limits_by_section = {
        e.get("section", "").lower(): e for e in (article_type.get("section_word_limits") or [])
    }
    parts = []
    matched = set()
    for section in sections:
        entry = limits_by_section.get(section.lower())
        if entry is None:
            # loose match: section word limit's name appears inside the section heading, or vice versa
            for key, e in limits_by_section.items():
                if key and (key in section.lower() or section.lower() in key):
                    entry = e
                    matched.add(key)
                    break
        else:
            matched.add(section.lower())
        if entry and entry.get("limit"):
            parts.append(f"{section} (≤{entry['limit']} words)")
        else:
            parts.append(section)
    # section word limits that didn't match any required_sections entry -- append separately rather than drop
    for key, e in limits_by_section.items():
        if key not in matched and e.get("limit"):
            parts.append(f"{e['section']} (≤{e['limit']} words)")
    return "; ".join(parts)


def _count_range_str(cr: dict | None) -> str:
    """CountRange ({min, max, notes}) -> a plain range string, e.g. '12-20' or 'up to 50'."""
    if not cr or (cr.get("min") is None and cr.get("max") is None):
        return ""
    lo, hi = cr.get("min"), cr.get("max")
    if lo is not None and hi is not None and lo != hi:
        range_str = f"{lo}-{hi}"
    elif hi is not None:
        range_str = f"up to {hi}" if lo is None else str(hi)
    else:
        range_str = f"at least {lo}"
    return f"{range_str} ({cr['notes']})" if cr.get("notes") else range_str


def _figure_limits_str(article_type: dict) -> str:
    parts = []
    for f in article_type.get("figure_limits") or []:
        lo, hi, counts = f.get("min"), f.get("max"), f.get("counts") or "figures"
        if lo is not None and hi is not None and lo != hi:
            range_str = f"{lo}-{hi}"
        elif hi is not None:
            range_str = f"up to {hi}"
        elif lo is not None:
            range_str = f"at least {lo}"
        else:
            range_str = None
        piece = f"{range_str} {counts}" if range_str else counts
        if f.get("notes"):
            piece += f" ({f['notes']})"
        parts.append(piece)
    return "; ".join(parts)


def record_to_rows(record: dict) -> list[list]:
    """One row per article type; journal-level fields repeat across those rows."""
    issn = record.get("issn") or {}
    article_types = record.get("article_types") or [{}]

    robots_v, robots_url, robots_notes = _sourced(record, "robots_txt_allowed")
    peer_v, peer_url, peer_notes = _sourced(record, "peer_review_model")
    preprint_v, preprint_url, _ = _sourced(record, "preprint_policy")
    ai_v, ai_url, _ = _sourced(record, "ai_use_policy")
    latex_v, latex_url, latex_notes = _sourced(record, "latex_accepted")
    template_v, template_src_url, template_notes = _sourced(record, "template_provided")
    orcid_v, orcid_url, orcid_notes = _sourced(record, "orcid_required")
    peer_v = _join(peer_v) if isinstance(peer_v, list) else peer_v  # value is a category list, e.g. ["single-anonymized", "double-anonymized"]

    rows = []
    for at in article_types:
        word_limit = at.get("total_word_limit") or {}
        rows.append([_na(v) for v in [
            record.get("journal"),
            record.get("publisher"),
            issn.get("print"),
            issn.get("electronic"),
            record.get("url"),
            record.get("date_scraped"),
            record.get("source"),
            robots_v, robots_url, robots_notes,
            peer_v, peer_url, peer_notes,
            preprint_v, preprint_url,
            ai_v, ai_url,
            latex_v, latex_url, latex_notes,
            template_v, template_src_url, template_notes,
            record.get("template_url"),
            orcid_v, orcid_url, orcid_notes,
            _join(record.get("languages_accepted")),
            at.get("type"),
            at.get("source_url"),
            at.get("description"),
            at.get("submission_mode"),
            word_limit.get("min"),
            word_limit.get("max"),
            word_limit.get("unit"),
            _join(word_limit.get("excludes")),
            word_limit.get("notes"),
            _required_sections_str(at),
            _figure_limits_str(at),
            _count_range_str(at.get("reference_limit")),
            at.get("reference_style"),
            _count_range_str(at.get("author_limit")),
            _join(at.get("required_statements")),
            at.get("notes"),
            record.get("remarks"),
            _join(record.get("needs_review")),
        ]])
    return rows


def build_workbook(records: list[dict]) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Journals"
    ws.append(COLUMNS)
    ws.freeze_panes = "A2"

    for record in records:
        for row in record_to_rows(record):
            ws.append(row)

    for idx, header in enumerate(COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = min(max(len(header) + 2, 14), 45)

    return wb


def load_latest_records(data_dir: Path = DATA_SCRAPES_DIR) -> list[dict]:
    records = []
    for latest_path in sorted(data_dir.glob("*/latest.json")):
        with latest_path.open(encoding="utf-8") as f:
            records.append(json.load(f))
    return records


def main() -> Path:
    records = load_latest_records()
    if not records:
        raise SystemExit(f"No latest.json files found under {DATA_SCRAPES_DIR}")
    wb = build_workbook(records)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUTPUT_PATH)
    return OUTPUT_PATH


if __name__ == "__main__":
    path = main()
    print(f"Wrote {path}")
