# LLM-based extraction (redrafted against your real vLLM install; still untested live)

A third approach, alongside the two already in this repo:
- `journal_scrapers/1476-4687_nature/scrape.py` -- a real parser: fetches pages and
  re-derives facts via regex every time it runs. Expensive to build, free to re-run forever.
- `journal_scrapers/1756-1833_bmj/extract.py` (and similar) -- a frozen transcript: Claude
  read the page once, in conversation, and hand-wrote the resulting values as code. Cheap to
  produce once, but not re-runnable against a changed page without a human/Claude reading it again.
- **This folder** -- calls a model (Qwen/Llama on your HPC cluster, via vLLM) programmatically,
  with no human/Claude in the loop at run time. This is the one that could actually scale to
  thousands of journals unattended, *if* the quality holds up -- which we haven't verified yet.

## What changed in this redraft (2026-09-18)

Learned by reading `../../../categorisation/code/03e_ndns_production_v2.py` /
`03f_ndns_production_llama33.py` (the two scripts that actually run Qwen2.5-72B-
Instruct-AWQ and Meta-Llama-3.3-70B-Instruct-AWQ-INT4 against this cluster's
vLLM install in production, at real scale) and by reading the installed vLLM
0.25.1 package itself (`envs/vllm-env`, shared with `categorisation`):

- **`guided_json` doesn't exist in the installed vLLM version.** Checked
  directly against `vllm/entrypoints/openai/chat_completion/protocol.py` --
  the old `extra_body={"guided_json": ...}` shape this file used to send
  would 400. `client.py`/`json_schema.py` now build a standard OpenAI
  `response_format={"type": "json_schema", ...}` request instead
  (`json_schema.as_response_format()`).
- **`categorisation`'s production scripts never use constrained decoding at
  all**, across hundreds of real jobs -- they prompt for JSON and parse it
  robustly instead (strip `<think>` reasoning tags, strip markdown fences,
  regex out the JSON body, retry per-item on a miss). `client.py` now does
  both: tries `response_format` first, and falls back to that same
  prompt+parse recipe (`_extract_json()`) if the server rejects it -- since
  whether guided decoding actually works well against this schema at 72B is
  still unverified, but the fallback path is the one thing proven at scale.
- **A pre-flight `check_vllm()`** now confirms the server is serving the
  exact `--model` you asked for before sending real requests --
  `categorisation` was bitten once by a stale server left on a compute node
  by an unrelated job silently answering on the same port.
- **`run_extract.sh`** (new) -- a SLURM launcher that starts vLLM, waits for
  it, runs `client.py`, tears it down. Without this, `client.py` had nothing
  to actually connect to on the HPC. Model names, conda env, module loads,
  and the wait-loop are copied from `categorisation`'s generic launchers
  (including the `|| true` on the `curl` poll -- without it, `set -euo
  pipefail` kills the job in ~8 seconds before vLLM finishes loading, a real
  bug documented in `categorisation/CLAUDE.md`). One difference:
  `--max-model-len 32768`, not `categorisation`'s validated `12000` -- this
  project's longest fetched page (BMJ's `article-types.md`, ~92KB) is
  ~23k tokens by this project's own `len//4` estimate, which would 400 at
  12000. Raising it is cheap on this cluster's hardware (see
  `run_extract.sh`'s header comment for why).
- **`pip install trafilatura`** still needs to be run once against
  `envs/vllm-env` -- it's not currently installed there (checked directly),
  so `clean_text.py` will fail before `client.py` is ever reached.

## Multi-page journals (added 2026-09-18)

A journal's guidance is usually spread across several pages (see schema.py's
docstring on `SourcedValue`/`ArticleType.source_url`) -- `client.py` only
ever reads one `--page` per call, which is fine for a single-page journal
like BMJ but not for Nature, whose real ground truth
(`data_scrapes/json/0028-0836.json`) was assembled from 8 separate pages by
its bespoke `scrape.py`.

- **`page_manifests.py`** -- hand-researched `(page, source_url)` lists per
  journal ISSN, the same kind of data as `common/direct_fetch.py`'s
  `TARGETS`. Nature's 8 entries are transcribed from `scrape.py`'s own URL
  constants, so they're the actual URLs that produced `0028-0836.json`, not
  re-researched. Add an entry here for any other multi-page journal before
  running it through `extract_journal.py`.
- **`extract_journal.py`** (new) -- loops `client.py`'s `extract_page()`
  over every page in an ISSN's manifest against one already-loaded vLLM
  server (looping in-process, not one SLURM submission per page -- 8 pages
  as 8 separate model loads would burn ~2.5h before any real extraction
  happens), then merges the per-page records into one whole-journal
  `data_scrapes/llm_debug/<issn>/<date>.llm.full.json` via `merge_records()` -- first-non-null-wins
  per top-level field, article types concatenated with duplicate-name
  collisions flagged in `remarks` rather than silently overwritten,
  `needs_review` reconciled so a field resolved by one page isn't still
  flagged from another. Each page's own
  `data_scrapes/llm_debug/<issn>/<date>.llm.<page>.json`/`.audit.json` is still written too, for
  a narrower per-page diff (see "Suggested first validation" below).
  `merge_records()` was checked offline against
  synthetic multi-page input before trusting it on a real run -- see the
  assertions in this file's own commit/session history if you want the
  exact cases covered (cross-page field resolution, duplicate article-type
  names, `needs_review` reconciliation all passed).
- **`run_extract.sh`** now defaults to multi-page mode (`extract_journal.py`
  against the full manifest) whenever `PAGE` isn't set at submission time;
  pass `PAGE`+`SOURCE_URL` together for the old single-page behavior (e.g.
  re-running just one page after a prompt tweak), or `PAGES` (plural) to
  restrict multi-page mode to a comma-separated subset of the manifest.

## Files

- `clean_text.py` -- converts already-fetched HTML into clean Markdown (trafilatura --
  identifies real article content and discards nav/boilerplate, same role Mozilla Readability
  plays in `archive/example_webarchive_API_code/`, ported to Python so this whole pipeline is
  one runtime). Run this first. Unlike everything else in this folder, this one IS tested --
  it's just pip packages, no HPC/vLLM needed to check it -- and it's already been run against
  all 21 fetched journals; see its docstring for the Crelle/BMJ validation.
- `json_schema.py` -- generates a JSON Schema from `common/schema.py`'s dataclasses, for vLLM's
  `guided_json` (or `--inline` for a fully-expanded version, if your guided-decoding backend
  doesn't handle `$ref` well -- backend support varies and we couldn't test which you have).
- `prompts.py` -- the system prompt (extraction rules -- don't guess, target vs. ceiling vs.
  range, the categorical vocabularies, what's out of scope) plus a real few-shot example: the
  actual `clean_text.py` output for Annals of Mathematics' page, paired with its actual verified
  JSON. Matters that the example's input format matches what real queries look like.
- `verify.py` -- pulls the numeric/categorical claims out of an extraction result and checks a
  second model call's supporting quotes are real substrings of the source text. Free text
  fields (notes, description) aren't checked this way -- there's no crisp claim to verify a
  quote against for open-ended prose.
- `client.py` -- wires it together: reads the `.md` file `clean_text.py` produced, runs both
  model calls, verifies citations, saves `data_scrapes/llm_debug/<issn>/<date>.llm.json` and
  `data_scrapes/llm_debug/<issn>/<date>.llm.audit.json`.

## Setup

```
# once, against the shared envs/vllm-env (trafilatura is not currently installed there):
/data/biol-thriving/magd4194/envs/vllm-env/bin/pip install trafilatura

python clean_text.py --issn 0959-8138      # once per journal (or omit --issn to do all of them)

# on HPC: submit run_extract.sh instead of running client.py/extract_journal.py directly (see
# its header comment for the required --export vars) -- it starts vLLM, waits for it, runs the
# extraction, tears the server down. Default (PAGE unset) runs every page in page_manifests.py:
sbatch --job-name=extract_nature_qwen \
    --export=ALL,ISSN=0028-0836,JOURNAL_NAME=Nature,MODEL_KEY=qwen \
    run_extract.sh

# one page only (PAGE+SOURCE_URL set together):
sbatch --job-name=extract_nature_qwen_fmt \
    --export=ALL,ISSN=0028-0836,JOURNAL_NAME=Nature,PAGE=formatting-guide,\
SOURCE_URL=https://www.nature.com/nature/for-authors/formatting-guide,MODEL_KEY=qwen \
    run_extract.sh

# or, against an already-running server (e.g. an interactive salloc session):
python extract_journal.py --issn 0028-0836 --journal-name Nature \
    --base-url http://localhost:<port>/v1 --model Qwen/Qwen2.5-72B-Instruct-AWQ
```

`--issn` and `--page` point at an existing `data_scrapes/raw_html/<issn>/<page>.md` (produced
by `clean_text.py` from the `.html` `direct_fetch.py` already fetched) -- neither script here
fetches anything from the network itself. `--journal-name` is required on both scripts, since
it can no longer be derived from a `<issn>_<slug>` folder name the way it once was.

## What's genuinely untested

`clean_text.py` has been run for real, against all 21 fetched journals' actual pages -- see its
docstring for the specific validation (it independently found the Crelle content an earlier
manual read missed, and preserved BMJ's limit tables as real Markdown tables). Everything else
has only been checked for correctness against the real installed vLLM/openai packages and against
`categorisation`'s real production logs (schema generation produces valid JSON Schema, the
`response_format` shape matches what the installed vLLM 0.25.1 actually parses, message
construction is well-formed, the citation-verification logic was tested against BMJ's real source
text with a genuine quote, a fabricated one, and an honest "not found" -- all three behaved
correctly) -- not against a live model. What hasn't been tested: how Qwen/Llama actually respond
to these prompts. Expect to iterate on wording once you see real output, particularly:

- Whether `response_format` guided decoding is actually reliable/fast enough against this
  schema at 72B (categorisation's own production pipeline never uses it, for whatever reason --
  worth checking vLLM's server-side logs on a first real run for guided-decoding warnings/
  fallback-to-unguided messages, not just whether the call succeeds), or whether the
  `_extract_json()` fallback path ends up doing most of the real work in practice.
- Whether a 70B model reliably follows rule 2 (confirmed-absence vs. not-checked) and rule 5
  (peer review as a category list, not a sentence) without more few-shot examples than the one
  provided. If it doesn't, adding a second few-shot pair (maybe BMJ's Editorials, which has a
  real min/max range) is the natural next step.
- The actual unverified-claim rate on a first real run -- that number is the whole point of
  trying this, and we don't have it yet.
- Whether `--max-model-len 32768` is actually enough once run against real prompts (see
  `run_extract.sh`'s header comment for how that number was estimated) -- check the vLLM server
  log for a context-length 400 on the first BMJ run specifically, since that's the longest page.

## Suggested first validation

Run the full 8-page manifest against Nature (`sbatch ... --export=ALL,ISSN=0028-0836,
JOURNAL_NAME=Nature,MODEL_KEY=qwen run_extract.sh`, or the `llama` arm the same way), not BMJ and
not a single page -- Nature's ground truth (`data_scrapes/json/0028-0836.json`) came from a real
bespoke parser (`journal_scrapers/1476-4687_nature/scrape.py`, re-derives every fact from the
live pages) rather than a one-time hand-transcription like BMJ/Annals/Frontiers, so it's the most
rigorously checked baseline in the project to diff against, and now that `extract_journal.py`
covers every page the manifest lists, the comparison can be the *whole* `0028-0836.json`, not
just the `formatting-guide` subset an earlier draft of this section recommended.

**Two levels to diff at**:
- **`data_scrapes/llm_debug/0028-0836/<date>.llm.full.json`** (the merged record) against the
  whole of `data_scrapes/json/0028-0836.json` -- this is now a fair, complete comparison, since
  every field `0028-0836.json` has a `source_url` for should have come from a page
  `extract_journal.py` actually ran.
- **`data_scrapes/llm_debug/0028-0836/<date>.llm.<page>.json`** (per-page, e.g.
  `<date>.llm.formatting-guide.json`) against just the fields whose `source_url` in
  `0028-0836.json` matches that page -- useful for isolating which specific page's extraction is
  weak, or for a quick single-page re-check with
  `PAGE`+`SOURCE_URL` after a prompt tweak, without re-running all 8.

If a field the model should have caught comes back `null`/in `needs_review` in the merged output,
check `merge_records()`'s `remarks` field first -- a genuine cross-page collision (two pages both
claiming a value, or the same article-type name from two pages) is recorded there, not silently
dropped, and might be the actual explanation rather than the model missing it. Once Nature looks
clean, that's the point to move on to any of the other 14 journals nothing has verified yet.
