# Journal publication requirements scraper

Scrapes author-guideline pages per journal (word limits, required sections,
figure limits, LaTeX/template support, peer review model, preprint/AI-use
policy, etc.) into a shared JSON schema.

## Layout

```
journal_scrapers/
  common/
    schema.py         # JournalRecord / ArticleType / SourcedValue dataclasses -- the shared output shape
    base_scraper.py    # BaseJournalScraper: robots.txt check, fetch, save JSON + raw HTML
    robots.py           # our own robots.txt matcher (Python's stdlib one doesn't support wildcards -- see below)
    direct_fetch.py      # fetches raw HTML/PDF for every journal confirmed NOT blocked -- one TARGETS entry per journal, run this first
    render_js.py          # Playwright JS-rendering, for the rare page whose content only loads client-side
    json_to_excel.py       # flattens scraped JSON into an Excel overview
  <issn>_<journal-slug>/
    scrape.py                # a full bespoke scraper (fetch -> parse -> JSON): only Nature so far
    extract.py                # reads already-fetched HTML, no live fetch/parsing -- values are hand-transcribed
                                # from a one-time read (BMJ, Annals of Mathematics, Frontiers in Sustainable Food Systems)
  llm_extract/
    clean_text.py               # HTML -> clean Markdown (trafilatura); run this first -- tested against all 21 fetched journals
    json_schema.py                # generates a JSON Schema from schema.py, for constrained LLM decoding (e.g. vLLM guided_json)
    prompts.py                      # extraction + citation-verification prompt templates, with a real few-shot example
    verify.py                         # checks a model's cited quotes are real substrings of the source text
    client.py                           # runs both calls against a self-hosted model (Qwen/Llama via vLLM) -- see its README
data_scrapes/
  <issn>_<journal-slug>/
    raw_html/                 # fetched pages/PDFs -- the corpus direct_fetch.py and scrape.py write into
    latest.json                # most recent structured extraction (only exists where a scrape.py has been built)
    YYYY-MM-DD.json              # dated snapshots
docs/
  RSETraining AI Project.xlsx    # original source spreadsheet: candidate journals + proposed fields
  journal_list.rtf                # expanded/updated candidate journal list
  journal_access_survey.csv        # per-journal access status (open / WAF-blocked / needs Wayback / etc.)
  usage_log.csv                     # cost-per-phase tracking, from Claude Code's /cost output
archive/
  example_webarchive_API_code/       # Node.js Wayback Machine exploration (Readability+Turndown); not part of the live pipeline
```

`<issn>` is the electronic ISSN where available (falls back to print ISSN).

## The three-phase workflow

0. **Discover the right URL(s).** Not automated -- this is currently Claude reading a journal's
   site by hand each time: finding the "for authors" nav, judging whether a page has real
   content or is just a table of contents, following companion links, checking for in-page
   anchors that a plain link-scan misses (this cost real rework on Crelle -- read the whole
   page, don't just scan `<a href>` tags). See "Known gap" below -- this step, not extraction,
   is the actual scaling bottleneck.
1. **Fetch HTML.** For a journal confirmed accessible in `docs/journal_access_survey.csv`, add
   its page(s) to `direct_fetch.py`'s `TARGETS` list and run it. This is deliberately dumb --
   fetch and save, no parsing -- but the `note` field on each entry documents *why* that page
   was chosen (often a "submission guidelines" landing page is just a table of contents; the
   real numbers are one or two links deeper). If a page's content only loads via JavaScript
   (confirmed by near-zero visible text despite a large HTML payload), use `render_js.py` to
   find what it actually links to, then fetch that directly -- Playwright is for rendering, not
   for getting past blocks (see Compliance below).
2. **Extract structured fields.** Turn the saved HTML into JSON matching `schema.py`. Three
   different approaches exist in this repo, at different points on a build-cost vs. re-runnable
   spectrum:
   - **Bespoke parser** (`<slug>/scrape.py`, only Nature): real regex/BeautifulSoup logic that
     re-derives every fact from the live page each time it runs. Expensive to build, free to
     re-run forever, and will tell you (via failed matches) if the page changes.
   - **Hand-transcribed** (`<slug>/extract.py`, BMJ / Annals of Mathematics / Frontiers in
     Sustainable Food Systems): Claude read the already-fetched HTML once and wrote the
     resulting values directly as code -- no parsing logic at runtime at all. Cheaper to
     produce than a bespoke parser, but it's a frozen snapshot: re-running it just re-emits the
     same JSON, and a changed page won't be noticed until someone reads it again by hand.
   - **LLM-based** (`llm_extract/`, untested against real models): calls a self-hosted model
     (Qwen/Llama via vLLM) programmatically against the already-fetched HTML, with no human/
     Claude in the loop at run time -- the only one of the three that could plausibly scale to
     the rest of the candidate list unattended, if the quality holds up. See its own README for
     setup and what's still unverified.

## Known gap: URL discovery doesn't scale

`direct_fetch.py` looks like a scraper but isn't one -- it only fetches URLs Claude already
found. Every entry in its `TARGETS` list represents real per-journal research (WebSearch, curl
probing, reading whole pages rather than link-scanning, finding companion pages, working around
cookie-redirect dances and CAPTCHA walls). That doesn't show up in the script, and it's the same
"one bespoke thing per journal" problem this project already backed away from once (bespoke
*parsers*, replaced by `extract.py`/`llm_extract/`) -- it just relocated to *discovery*. A good
result from `llm_extract/` on HPC proves the last stage of the pipeline works; it doesn't prove
the pipeline scales, because discovery is still manual.

Two proposed fixes, neither built yet:

1. **Agentic URL-discovery step** -- an LLM-driven crawler that does what Claude has been doing
   by hand: start at a journal homepage, look for "for authors" nav, fetch candidates, judge
   content-richness vs. a stub/table-of-contents, follow companion links, stop when satisfied.
   Real agent-engineering work, not started.
2. **Platform-pattern reuse** -- a large fraction of journals sit on a handful of platforms with
   predictable URL templates. Already confirmed in this project's own data: Springer is
   `link.springer.com/journal/<id>/submission-guidelines` for at least 5 journals here
   (Mathematische Annalen, Inventiones Mathematicae, Selecta Mathematica, JHEP, General
   Relativity and Gravitation). Once a platform's template is known, adding another journal on
   it is a cheap ID/slug lookup, not a research session -- reframes scaling from O(journals) to
   roughly O(platforms) + cheap lookups. Doesn't help the platforms that are WAF-blocked
   regardless (Elsevier, Wiley, Science, PNAS), and doesn't cover long-tail independent journals
   with no shared template.

(Checked github.com/Agents4Academia-AI/prior as a possible starting point for option 1 -- not
directly applicable, it's a literature-synthesis/knowledge-graph tool over academic papers via
OpenAlex/arXiv, not a web-navigation agent for arbitrary publisher sites. Worth borrowing anyway:
it uses cross-model agreement as one confidence signal alongside extraction score -- relevant if
testing more than one HPC model, though citation-verification, already built into
`llm_extract/verify.py`, is the more direct defense against fabrication.)

## Why the schema looks the way it does

Word limits, required sections, section word counts, figure limits and
reference limits usually vary **by article type** within a journal (Research
Article vs Review vs Letter...), not just by journal. So those fields live on
`ArticleType` entries nested under each `JournalRecord`, not as flat top-level
columns. See `journal_scrapers/common/schema.py` for the full shape.

Journal guideline pages are prose, not tables -- exact numbers aren't always
available (e.g. Nature gives a word-count *range* depending on page count,
not a single limit). Where a scraper can't reduce something to a clean value,
it leaves the field `null`/`notes`-only and adds the field name to
`needs_review`, rather than guessing. `needs_review` means "not yet checked
one way or the other" -- it's different from a confirmed "no number is
published" (e.g. Nature's commissioned Reviews), which is recorded as a
normal value with an explanatory note, not flagged for review.

A journal's guidance is usually spread across several pages, so a single
`JournalRecord.url` can't honestly be "the" source for every field. Fields
read from a page other than `url` are wrapped in `SourcedValue`
(`{value, source_url, notes}`) so each fact can be traced back to exactly
where it came from -- see the docstring in `schema.py`.

## Compliance

Every fetch goes through robots.txt first, via `common/robots.py` -- **not**
Python's stdlib `urllib.robotparser`, which doesn't implement `*` wildcards
or empty-`Disallow` semantics and silently mis-reads very common real-world
robots.txt patterns (this cost us real debugging time -- see git history /
conversation log if curious). The scraper identifies itself with its own
honest User-Agent string in `common/base_scraper.py` -- not a browser UA, and
not an AI-crawler UA (some publishers, e.g. nature.com, disallow
`anthropic-ai`/`ClaudeBot`/`GPTBot` by name in robots.txt; this project's bot
is a distinct, separately-named identity).

For publishers whose WAF actively blocks non-browser clients (confirmed via a
live 403, not just robots.txt), we do not attempt to get past it -- no
stealth/evasion automation, regardless of how legitimate the downstream
purpose is. `render_js.py`'s use of Playwright is different in kind: it's
only ever used on pages that are *not* blocked (robots.txt allows us, no WAF
403), purely to execute the page's own JavaScript so we see what a normal
browser would -- there is no detection being evaded. See
`docs/journal_access_survey.csv` for the current open/blocked breakdown, and
its `recommended_approach` column for what to do about a blocked one
(currently: flag it, or check Wayback Machine coverage -- not yet automated).

Before adding a new journal, also sanity-check the publisher's Terms of Use
-- robots.txt being silent isn't the same as ToS permission.

## Adding a new journal

**If it's accessible directly** (check/add to `docs/journal_access_survey.csv` first):
1. Find its ISSN and the actual page(s) with real formatting content -- read
   the page, don't just link-scan (a landing page's nav links can miss
   in-page anchor sections entirely; this has bitten us more than once).
2. Add a `TARGETS` entry to `direct_fetch.py` with those URLs and a `note`
   explaining what's there / what's missing.
3. Run `python journal_scrapers/common/direct_fetch.py`.
4. (Optional, not yet standard) Write a `scrape.py` like Nature's to extract
   structured fields into `data_scrapes/<issn>_<slug>/latest.json`.

**If it's blocked**: don't build automated workarounds. Check
`docs/journal_access_survey.csv`'s notes for what's already known about that
publisher's platform (many blocked journals share a platform -- Elsevier,
Wiley, etc. -- so one finding often applies to several journals at once).

## Status

- 4 journals have a full structured extraction: `1476-4687_nature` (bespoke
  `scrape.py`, 7 article types, all journal-level fields resolved and cited
  except Registered Reports' word/figure/reference limits), and
  `1756-1833_bmj` / `1939-8980_annals-of-mathematics` /
  `2571-581X_frontiers-sustainable-food-systems` (hand-transcribed
  `extract.py`, built to test extraction approach/cost -- see the "Extract
  structured fields" section above).
- 21 journals total have raw HTML/PDF fetched into `data_scrapes/` (see
  `direct_fetch.py`'s `TARGETS` and `docs/journal_access_survey.csv`) --
  structured extraction not yet built for the other 17.
- `llm_extract/` is a prototype for automating extraction against
  self-hosted models (Qwen/Llama via vLLM) -- designed and unit-tested in
  isolation, but not yet run against a real model. See its README before
  using it.
- `docs/journal_access_survey.csv` tracks the rest of the candidate list
  (~40 journals): which are directly accessible, which are WAF-blocked, and
  which need further work (Wayback Machine checks not yet done for most
  blocked ones; CQG/JPhysG are missing one CAPTCHA-gated field each;
  Perspectives in Ecology and Conservation's PDF has unrecoverable numbers
  without OCR).

Note: `docs/RSETraining AI Project.xlsx` currently lists "Nature
Sustainability" twice in the original sheet -- worth checking whether that
was intentional.
