var { Readability } = require('@mozilla/readability');
var { JSDOM } = require('jsdom');

var TurndownService = require('turndown')
var turndownService = new TurndownService()

Readability = require("@mozilla/Readability").Readability

async function getHTML(url) {
  // Like the browser fetch API, the default method is GET
  const response = await fetch(url);
  const data = await response.text();

  return data;
}


async function simplifyHTML(data) {
	var doc = new JSDOM(data);
	var article = new Readability(doc.window.document).parse();

 	return article.content;
}

async function HTML2Markdown(html) {
	return turndownService.turndown(html)
}

// TODO:
	// web archive api?
	// Scraper
	// Allice morell docs
	// https://archive.org/help/wayback_api.php

async function main() {
	// const testURL = "https://msp.org/gt/about/journal/submissions.html"	
	// const testURL = "https://www.sciencedirect.com/journal/advances-in-mathematics/publish/guide-for-authors" // Blocked
	// const testURL = "https://academic.oup.com/eurheartj/pages/General_Instructions" // NULL
	// const testURL = "https://www.lms.ac.uk/publications/jlms#submit-to-the-journal"	
	// const testURL = "https://link.springer.com/brands/springer/journal-policies"	
	// const testURL = "https://www.pnas.org/author-center/submitting-your-manuscript" // blocked
	const testURL = "https://web.archive.org/web/20260617040225/https://www.pnas.org/author-center/submitting-your-manuscript"
	
		
	const rawHTML = await getHTML(testURL);
	const simplifiedHTML = await simplifyHTML(rawHTML);
	const markdown = await HTML2Markdown(simplifiedHTML)
	

	console.log(markdown);
}

main().catch(console.error);