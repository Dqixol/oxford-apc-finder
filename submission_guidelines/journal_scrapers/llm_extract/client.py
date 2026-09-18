"""Runs the two-call extraction (see prompts.py) against a vLLM-served model
for one journal already fetched by direct_fetch.py, verifies each claim's
citation against the source text, and saves the result.

UNTESTED against your actual Qwen/Llama endpoints -- I don't have network
access to your HPC cluster from this environment, so this has only been
checked for: valid Python, correct schema generation, and correct message
structure (see json_schema.py and prompts.py's own inline checks). Treat
this as a solid starting point to iterate from, not a working guarantee.

Requires: pip install openai trafilatura  (the `openai` package is just the
HTTP client shape -- works against any OpenAI-compatible server, including
vLLM's, no OpenAI account needed)

Run clean_text.py first -- this reads the .md file it produces, not the raw
.html directly (a flat text-dump of raw HTML loses table/heading structure
that turned out to matter for real pages -- see clean_text.py's docstring).

Usage:
    python clean_text.py --slug 1756-1833_bmj        # once, produces .md files
    python client.py --slug 1756-1833_bmj --page article-types \\
        --base-url http://<your-hpc-host>:8000/v1 --model Qwen2.5-72B-Instruct

If your vLLM version's structured-output parameter differs from
`guided_json` (see EXTRACT_MODEL below), that's the one line to change --
newer vLLM releases have moved some of this to a `response_format`
matching OpenAI's `json_schema` shape. Check `vllm serve --help` or your
version's docs for `--guided-decoding-backend` and how it expects the
schema to be passed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from json_schema import build_json_schema, inline  # noqa: E402
from prompts import build_citation_check_messages, build_extraction_messages  # noqa: E402
from verify import extract_claims, verify_claims  # noqa: E402

DATA_SCRAPES_DIR = Path(__file__).resolve().parents[2] / "data_scrapes"


def call_model(client, model: str, messages: list[dict], guided_json: dict | None = None, max_tokens: int = 4096) -> str:
    extra_body = {"guided_json": guided_json} if guided_json is not None else {}
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0,  # deterministic extraction, not creative generation
        extra_body=extra_body,
    )
    return resp.choices[0].message.content


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="e.g. 1756-1833_bmj (the data_scrapes/<slug> folder)")
    ap.add_argument("--page", required=True, help="page filename without .html, e.g. article-types")
    ap.add_argument("--journal-name", default=None, help="defaults to the slug's second half if omitted")
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--base-url", required=True, help="your vLLM OpenAI-compatible endpoint, e.g. http://host:8000/v1")
    ap.add_argument("--model", required=True, help="the model name as vLLM is serving it")
    ap.add_argument("--use-inline-schema", action="store_true", help="use the fully-expanded schema instead of $ref-based, if your backend doesn't support $ref")
    args = ap.parse_args()

    from openai import OpenAI  # deferred import so json_schema.py/prompts.py stay importable without the package

    client = OpenAI(base_url=args.base_url, api_key="not-needed")  # vLLM typically doesn't require a real key

    md_path = DATA_SCRAPES_DIR / args.slug / "raw_html" / f"{args.page}.md"
    if not md_path.exists():
        html_path = md_path.with_suffix(".html")
        hint = "run clean_text.py first" if html_path.exists() else "has direct_fetch.py been run for this journal/page?"
        raise SystemExit(f"No such file: {md_path} -- {hint}")

    page_text = md_path.read_text(encoding="utf-8")
    journal_name = args.journal_name or args.slug.split("_", 1)[1].replace("-", " ").title()
    from datetime import date
    today = date.today().isoformat()

    schema = build_json_schema()
    if args.use_inline_schema:
        schema = inline(schema)

    # -- Call 1: structured extraction --
    messages = build_extraction_messages(journal_name, args.source_url, today, page_text)
    raw = call_model(client, args.model, messages, guided_json=schema)
    try:
        record = json.loads(raw)
    except json.JSONDecodeError:
        print("Model output was not valid JSON despite guided_json -- printing raw output for debugging:")
        print(raw)
        raise

    # -- Call 2: citation check on whatever non-null claims call 1 made --
    claims = extract_claims(record)
    if claims:
        check_messages = build_citation_check_messages(page_text, [c["claim"] for c in claims])
        check_raw = call_model(client, args.model, check_messages, guided_json=None, max_tokens=2048)
        try:
            quotes = json.loads(check_raw)
        except json.JSONDecodeError:
            print("Citation-check output was not valid JSON -- skipping verification, printing raw:")
            print(check_raw)
            quotes = []
        report = verify_claims(claims, quotes, page_text)
    else:
        report = []

    out_dir = DATA_SCRAPES_DIR / args.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{today}.llm.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / f"{today}.llm.audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    unverified = [r for r in report if not r["verified"]]
    print(f"Wrote {out_dir}/{today}.llm.json ({len(claims)} claims, {len(unverified)} unverified)")
    if unverified:
        print("Unverified claims (model couldn't quote real supporting text -- treat these as suspect):")
        for r in unverified:
            print(f"  - {r['claim']}")


if __name__ == "__main__":
    main()
