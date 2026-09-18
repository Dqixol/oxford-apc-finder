"""Runs the two-call extraction (see prompts.py) against a vLLM-served model
for one journal already fetched by direct_fetch.py, verifies each claim's
citation against the source text, and saves the result.

Verified against this cluster's actual setup (not run live yet -- no network
access to the HPC from this environment -- but checked directly against the
real installed packages, not assumed):
- vLLM 0.25.1 and openai 2.46.0 are what's installed in
  ../../../envs/vllm-env (the same shared conda env `categorisation` uses).
- That vLLM version's OpenAI-compatible server does NOT accept the older
  `extra_body={"guided_json": ...}` shape this file used to send (checked
  directly against envs/vllm-env/lib/python3.11/site-packages/vllm/
  entrypoints/openai/chat_completion/protocol.py) -- it wants the standard
  OpenAI `response_format={"type": "json_schema", ...}` shape instead, built
  by json_schema.py's `as_response_format()`.
- `categorisation/code/03e_ndns_production_v2.py` /
  `03f_ndns_production_llama33.py` run these exact two models (Qwen2.5-72B-
  Instruct-AWQ, Meta-Llama-3.3-70B-Instruct-AWQ-INT4) against this same vLLM
  install in production, at real scale (over a million rows classified) --
  but never use guided_json/response_format at all. They get JSON out by
  prompting for it plus a robust parser (strip <think> reasoning tags, strip
  markdown fences, regex out the JSON body) with a per-item retry on a miss.
  That's the one thing actually proven against these models on this
  cluster, so `call_model()` below tries response_format first (a genuine
  decoding constraint, worth having when it works) and falls back to that
  same prompt+parse recipe if the server rejects it -- see `_extract_json()`.

Requires: pip install openai trafilatura (trafilatura is NOT currently
installed in envs/vllm-env -- `pip install trafilatura` into it once, or the
clean_text.py step will fail before this script is ever reached)

Run clean_text.py first -- this reads the .md file it produces, not the raw
.html directly (a flat text-dump of raw HTML loses table/heading structure
that turned out to matter for real pages -- see clean_text.py's docstring).

Usage (see run_extract.sh for the SLURM wrapper that actually starts vLLM):
    python clean_text.py --issn 0959-8138        # once, produces .md files
    python client.py --issn 0959-8138 --page article-types --journal-name "The BMJ" \\
        --source-url https://www.bmj.com/about-bmj/resources-authors/article-types \\
        --base-url http://<your-hpc-host>:8000/v1 --model Qwen/Qwen2.5-72B-Instruct-AWQ
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from json_schema import as_response_format, build_json_schema, inline  # noqa: E402
from prompts import build_citation_check_messages, build_extraction_messages  # noqa: E402
from verify import extract_claims, verify_claims  # noqa: E402

DATA_SCRAPES_DIR = Path(__file__).resolve().parents[2] / "data_scrapes"


def check_vllm(base_url: str, model: str) -> None:
    """Confirms the server at base_url is actually serving `model` before
    sending real requests. Mirrors categorisation/code/03e_ndns_production_v2.py's
    check_vllm() -- that project was bitten once (2026-07-30, job 8383975) by
    a stale vLLM server left on a compute node by an unrelated earlier job,
    serving a different model on the same port; a check that only confirms
    *a* model is loaded (not *this* model) silently passes against the wrong
    server and every real call then 404s deep into a run."""
    import requests

    models_url = base_url.rstrip("/")
    if not models_url.endswith("/models"):
        models_url += "/models"
    try:
        r = requests.get(models_url, timeout=10)
        served = [m["id"] for m in r.json().get("data", [])]
    except Exception as e:
        raise SystemExit(f"Cannot reach vLLM at {base_url}: {e}")
    if model not in served:
        raise SystemExit(
            f"vLLM at {base_url} is serving {served}, not the expected {model!r} -- "
            f"likely a stale server left on this node from an earlier job, or --model "
            f"doesn't match what was passed to `vllm serve`/`python -m vllm.entrypoints."
            f"openai.api_server`. Refusing to proceed rather than silently 404ing later."
        )


def _extract_json(raw: str) -> str:
    """Strips reasoning traces, markdown fences, and any leading/trailing prose
    around a top-level JSON value -- the same recovery categorisation's
    clean_json() applies at scale against these exact models, generalized to
    handle either shape this file's two calls produce: an object ({...}) for
    the extraction call, a list ([...]) for the citation-check call (see
    prompts.py). Needed even when response_format was requested: the fallback
    path in call_model() never got a real decoding constraint, and even a
    constrained call has been seen (in categorisation's production logs) to
    occasionally wrap output in <think>...</think> for Qwen's reasoning-
    capable checkpoints."""
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    matches = [m for m in (re.search(r"\{.*\}", raw, flags=re.DOTALL), re.search(r"\[.*\]", raw, flags=re.DOTALL)) if m]
    if not matches:
        return raw
    return min(matches, key=lambda m: m.start()).group(0).strip()


def call_model(
    client,
    model: str,
    messages: list[dict],
    schema: dict | None = None,
    schema_name: str = "journal_record",
    max_tokens: int = 4096,
) -> str:
    """`schema`, when given, is a JSON Schema (as from json_schema.build_json_schema())
    -- wrapped here via as_response_format() into the shape vLLM 0.25.1's
    server actually accepts. If the server rejects that request (a different
    vLLM version, or a guided-decoding backend that can't compile a schema
    this large -- untested against your real 72B/AWQ setup, so a real
    possibility), falls back to an unconstrained call and lets _extract_json()
    do the work instead, matching categorisation's proven-at-scale pattern.

    Uses max_completion_tokens, not max_tokens, in the actual API call --
    that's what categorisation's production scripts send against this same
    vLLM install; max_tokens still works via the openai client's back-compat
    shim, but there's no reason to diverge from the one thing that's
    confirmed to work here."""
    base_kwargs = dict(model=model, messages=messages, max_completion_tokens=max_tokens, temperature=0)

    if schema is not None:
        try:
            resp = client.chat.completions.create(
                **base_kwargs,
                response_format=as_response_format(schema, schema_name),
            )
            return _extract_json(resp.choices[0].message.content)
        except Exception as e:
            print(
                f"  response_format json_schema call failed ({e}) -- falling back to an "
                f"unconstrained call + JSON extraction (categorisation's proven pattern "
                f"against this same vLLM install)."
            )

    resp = client.chat.completions.create(**base_kwargs)
    return _extract_json(resp.choices[0].message.content)


def extract_page(
    client,
    model: str,
    *,
    issn: str,
    page: str,
    source_url: str,
    journal_name: str,
    use_inline_schema: bool = False,
    out_suffix: str | None = None,
) -> tuple[dict, list[dict]]:
    """Runs both calls (extraction + citation check) against one already-fetched
    page and writes its two output files, exactly what main() used to do
    inline. Pulled out as its own function so extract_journal.py can call it
    once per page of a multi-page journal against a single already-loaded
    vLLM server, instead of every page needing its own `client.py` process
    (and, if driven through run_extract.sh, its own ~20-minute model load).

    `out_suffix` lets a multi-page caller keep each page's output distinct
    (e.g. "formatting-guide") instead of every page overwriting the same
    `<date>.llm.json` -- single-page callers (main(), below) leave it None
    and get the original filename back.

    Returns (record, report) so a caller can merge multiple pages' records
    -- see extract_journal.py's merge_records()."""
    md_path = DATA_SCRAPES_DIR / "raw_html" / issn / f"{page}.md"
    if not md_path.exists():
        html_path = md_path.with_suffix(".html")
        hint = "run clean_text.py first" if html_path.exists() else "has direct_fetch.py been run for this journal/page?"
        raise SystemExit(f"No such file: {md_path} -- {hint}")

    page_text = md_path.read_text(encoding="utf-8")
    from datetime import date
    today = date.today().isoformat()

    schema = build_json_schema()
    if use_inline_schema:
        schema = inline(schema)

    # -- Call 1: structured extraction --
    messages = build_extraction_messages(journal_name, source_url, today, page_text)
    raw = call_model(client, model, messages, schema=schema)
    try:
        record = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [{page}] Model output was not valid JSON even after fence/think-tag stripping -- printing raw output for debugging:")
        print(raw)
        raise

    # -- Call 2: citation check on whatever non-null claims call 1 made --
    claims = extract_claims(record)
    if claims:
        check_messages = build_citation_check_messages(page_text, [c["claim"] for c in claims])
        check_raw = call_model(client, model, check_messages, schema=None, max_tokens=2048)
        try:
            quotes = json.loads(check_raw)
        except json.JSONDecodeError:
            print(f"  [{page}] Citation-check output was not valid JSON -- skipping verification, printing raw:")
            print(check_raw)
            quotes = []
        report = verify_claims(claims, quotes, page_text)
    else:
        report = []

    out_dir = DATA_SCRAPES_DIR / "llm_debug" / issn
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = out_suffix or ""
    tag = f".{tag}" if tag else ""
    (out_dir / f"{today}.llm{tag}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / f"{today}.llm{tag}.audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    unverified = [r for r in report if not r["verified"]]
    print(f"  [{page}] wrote {out_dir}/{today}.llm{tag}.json ({len(claims)} claims, {len(unverified)} unverified)")
    if unverified:
        print(f"  [{page}] Unverified claims (model couldn't quote real supporting text -- treat these as suspect):")
        for r in unverified:
            print(f"    - {r['claim']}")

    return record, report


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Single-page extraction. For a journal whose guidance spans several pages "
        "(Nature and others -- see page_manifests.py), use extract_journal.py instead so all "
        "pages run against one already-loaded vLLM server."
    )
    ap.add_argument("--issn", required=True, help="e.g. 0959-8138 (the data_scrapes/<issn> folder -- print ISSN, or electronic if the journal has no print edition)")
    ap.add_argument("--page", required=True, help="page filename without .html, e.g. article-types")
    ap.add_argument("--journal-name", required=True, help="can't be derived from --issn alone, unlike the old <issn>_<slug> convention")
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--base-url", required=True, help="your vLLM OpenAI-compatible endpoint, e.g. http://host:8000/v1")
    ap.add_argument("--model", required=True, help="the model name as vLLM is serving it, e.g. Qwen/Qwen2.5-72B-Instruct-AWQ")
    ap.add_argument("--use-inline-schema", action="store_true", help="use the fully-expanded schema instead of $ref-based, if your backend doesn't support $ref")
    ap.add_argument("--skip-vllm-check", action="store_true", help="skip the pre-flight check that the server is actually serving --model (see check_vllm())")
    args = ap.parse_args()

    from openai import OpenAI  # deferred import so json_schema.py/prompts.py stay importable without the package

    if not args.skip_vllm_check:
        check_vllm(args.base_url, args.model)

    client = OpenAI(base_url=args.base_url, api_key="EMPTY")  # vLLM doesn't validate this; "EMPTY" matches categorisation's convention

    extract_page(
        client, args.model,
        issn=args.issn, page=args.page, source_url=args.source_url, journal_name=args.journal_name,
        use_inline_schema=args.use_inline_schema,
    )


if __name__ == "__main__":
    main()
