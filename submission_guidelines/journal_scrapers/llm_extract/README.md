# LLM-based extraction (experimental, untested against your models)

A third approach, alongside the two already in this repo:
- `journal_scrapers/1476-4687_nature/scrape.py` -- a real parser: fetches pages and
  re-derives facts via regex every time it runs. Expensive to build, free to re-run forever.
- `journal_scrapers/1756-1833_bmj/extract.py` (and similar) -- a frozen transcript: Claude
  read the page once, in conversation, and hand-wrote the resulting values as code. Cheap to
  produce once, but not re-runnable against a changed page without a human/Claude reading it again.
- **This folder** -- calls a model (Qwen/Llama on your HPC cluster, via vLLM) programmatically,
  with no human/Claude in the loop at run time. This is the one that could actually scale to
  thousands of journals unattended, *if* the quality holds up -- which we haven't verified yet.

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
  model calls, verifies citations, saves `<date>.llm.json` and `<date>.llm.audit.json`.

## Setup

```
pip install openai trafilatura
python clean_text.py --slug 1756-1833_bmj      # once per journal (or omit --slug to do all of them)
python client.py --slug 1756-1833_bmj --page article-types \
    --source-url https://www.bmj.com/about-bmj/resources-authors/article-types \
    --base-url http://<your-hpc-host>:8000/v1 --model <model-name-as-served>
```

`--slug` and `--page` point at an existing `data_scrapes/<slug>/raw_html/<page>.md` (produced
by `clean_text.py` from the `.html` `direct_fetch.py` already fetched) -- neither script here
fetches anything from the network itself.

## What's genuinely untested

`clean_text.py` has been run for real, against all 21 fetched journals' actual pages -- see its
docstring for the specific validation (it independently found the Crelle content an earlier
manual read missed, and preserved BMJ's limit tables as real Markdown tables). Everything else
has only been checked for correctness in isolation (schema generation produces valid JSON
Schema, message construction is well-formed, the citation-verification logic was tested against
BMJ's real source text with a genuine quote, a fabricated one, and an honest "not found" -- all
three behaved correctly). What hasn't been tested: how Qwen/Llama actually respond to these
prompts. Expect to iterate on wording once you see real output, particularly:

- Whether `guided_json` is accepted the way `client.py` sends it, or whether your vLLM version
  wants a different parameter (`response_format` with a `json_schema` type is the newer,
  OpenAI-matching convention in some versions) -- one line to change in `call_model()`.
- Whether a 70B model reliably follows rule 2 (confirmed-absence vs. not-checked) and rule 4
  (peer review as a category list, not a sentence) without more few-shot examples than the one
  provided. If it doesn't, adding a second few-shot pair (maybe BMJ's Editorials, which has a
  real min/max range) is the natural next step.
- The actual unverified-claim rate on a first real run -- that number is the whole point of
  trying this, and we don't have it yet.

## Suggested first validation

Run this against a journal we *already* have hand-extracted (BMJ, Annals of Mathematics, or
Frontiers in Sustainable Food Systems -- see `data_scrapes/*/latest.json`), and diff the
model's output against the known-good one. That gives a real accuracy read before trusting it
on any of the other 14 journals nothing has verified yet.
