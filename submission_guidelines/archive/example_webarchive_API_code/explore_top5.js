// Applies the Wayback-fetch + Readability + Turndown pipeline from main.js
// across the top 5 journals in the pilot list (first 5 rows of
// RSETraining AI Project.xlsx), saving raw HTML and simplified markdown for
// each so the later Python extraction step has a corpus to work from.
// Downloading/simplifying only -- no field extraction here yet.
//
// URLs below were validated by hand first (see project-publisher-access-survey
// memory / conversation history): Wayback's "nearest snapshot" auto-resolution
// doesn't always land on a good capture -- some snapshots are themselves
// archived redirect loops or archived block/error pages (the archiver's own
// crawler got blocked too). Where that happened, the URL here is pinned to a
// specific timestamp known to hold real content.

var { Readability } = require('@mozilla/readability');
var { JSDOM } = require('jsdom');
var TurndownService = require('turndown');
var fs = require('fs');
var path = require('path');

var turndownService = new TurndownService();

async function getHTML(url) {
  const response = await fetch(url);
  return { text: await response.text(), finalUrl: response.url, status: response.status };
}

async function getBinary(url) {
  const response = await fetch(url);
  return { buffer: Buffer.from(await response.arrayBuffer()), status: response.status };
}

async function simplifyHTML(data) {
  var doc = new JSDOM(data);
  var article = new Readability(doc.window.document).parse();
  return article; // null if Readability couldn't find an article
}

async function HTML2Markdown(html) {
  return turndownService.turndown(html);
}

// pages: one or more named pages per journal. type 'html' runs the full
// Readability+Turndown pipeline; type 'pdf' just downloads the file (parsing
// PDFs is a later-phase problem, not this one).
const targets = [
  {
    slug: 'nature',
    journal: 'Nature',
    note: 'Not blocked -- already scraped directly (see journal_scrapers/1476-4687_nature). Skipped here; Nature\'s cookie-auth redirect dance also makes Wayback\'s auto-resolve loop indefinitely, so it is not a useful Wayback test case anyway.',
    pages: [],
  },
  {
    slug: 'science',
    journal: 'Science',
    pages: [
      { name: 'authors', type: 'html', url: 'https://web.archive.org/web/2024/https://www.science.org/about/authors' },
    ],
  },
  {
    slug: 'pnas',
    journal: 'PNAS',
    pages: [
      { name: 'submitting', type: 'html', url: 'https://web.archive.org/web/20260617040225/https://www.pnas.org/author-center/submitting-your-manuscript' },
    ],
  },
  {
    slug: 'lancet',
    journal: 'The Lancet',
    note: 'Only good capture is from 2016 (a decade stale) -- everything since is redirect-chain only. Landing page is just a nav index; real detail is in the linked PDF.',
    pages: [
      { name: 'information-for-authors', type: 'html', url: 'https://web.archive.org/web/20160508192343/http://www.thelancet.com/lancet/information-for-authors' },
      { name: 'information-for-authors', type: 'pdf', url: 'https://web.archive.org/web/20160508192343/http://www.thelancet.com/pb/assets/raw/Lancet/authors/lancet-information-for-authors.pdf' },
    ],
  },
  {
    slug: 'nejm',
    journal: 'NEJM',
    note: 'article-types page has good captures only through 2019 -- from mid-2020 on, NEJM\'s WAF blocked the Internet Archive\'s own crawler too (archived captures ARE archived block pages). Pinned to a confirmed-good 2019 snapshot.',
    pages: [
      { name: 'home', type: 'html', url: 'https://web.archive.org/web/2023/https://www.nejm.org/author-center/home' },
      { name: 'article-types', type: 'html', url: 'https://web.archive.org/web/20191121095539/https://www.nejm.org/author-center/article-types' },
    ],
  },
];

async function processPage(outDir, page) {
  if (page.type === 'pdf') {
    const { buffer, status } = await getBinary(page.url);
    const outPath = path.join(outDir, `${page.name}.pdf`);
    fs.writeFileSync(outPath, buffer);
    console.log(`  [${page.name}] status=${status} pdf, ${buffer.length} bytes -> ${outPath}`);
    return { name: page.name, type: 'pdf', status, ok: status === 200, bytes: buffer.length };
  }

  const { text: rawHTML, finalUrl, status } = await getHTML(page.url);
  fs.writeFileSync(path.join(outDir, `${page.name}.raw.html`), rawHTML, 'utf-8');

  const article = await simplifyHTML(rawHTML);
  if (!article || !article.content) {
    console.log(`  [${page.name}] status=${status} resolved=${finalUrl} -- Readability found no article content`);
    return { name: page.name, type: 'html', status, finalUrl, ok: false, reason: 'no article extracted' };
  }

  const markdown = await HTML2Markdown(article.content);
  fs.writeFileSync(path.join(outDir, `${page.name}.simplified.md`), markdown, 'utf-8');
  console.log(`  [${page.name}] status=${status} resolved=${finalUrl}`);
  console.log(`    title="${article.title}" markdown=${markdown.length} chars`);
  return { name: page.name, type: 'html', status, finalUrl, ok: true, title: article.title, markdownLength: markdown.length };
}

async function main() {
  const results = [];
  for (const target of targets) {
    console.log(`\n=== ${target.journal} ===`);
    if (target.note) console.log(`  note: ${target.note}`);
    if (target.pages.length === 0) {
      results.push({ journal: target.journal, slug: target.slug, skipped: true, note: target.note });
      continue;
    }
    const outDir = path.join(__dirname, 'output', target.slug);
    fs.mkdirSync(outDir, { recursive: true });
    const pageResults = [];
    for (const page of target.pages) {
      try {
        pageResults.push(await processPage(outDir, page));
      } catch (e) {
        console.log(`  [${page.name}] FAILED: ${e.message}`);
        pageResults.push({ name: page.name, type: page.type, ok: false, reason: e.message });
      }
    }
    results.push({ journal: target.journal, slug: target.slug, note: target.note, pages: pageResults });
  }

  console.log('\n\n=== Summary ===');
  for (const r of results) {
    if (r.skipped) {
      console.log(`SKIP  ${r.journal}`);
      continue;
    }
    for (const p of r.pages) {
      console.log(`${p.ok ? 'OK  ' : 'FAIL'}  ${r.journal.padEnd(10)} ${p.name.padEnd(24)} ${p.ok ? (p.title ? `"${p.title}"` : `${p.bytes} bytes`) : p.reason}`);
    }
  }

  fs.writeFileSync(path.join(__dirname, 'output', 'summary.json'), JSON.stringify(results, null, 2), 'utf-8');
}

main().catch(console.error);
