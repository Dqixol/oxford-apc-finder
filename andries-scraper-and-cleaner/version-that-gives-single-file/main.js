/*
 * Load Libraries
 */
const fs = require('fs');
const { Readability } = require('@mozilla/readability');
const { JSDOM } = require('jsdom');
const TurndownService = require('turndown');
const commandLineArgs = require('command-line-args');
const turndownService = new TurndownService()

/*
 * Main function
 */
async function main() {
	const optionDefinitions = [
	  { name: 'input', alias: 'i', type: String },
	  { name: 'output', alias: 'o', type: String },
	  { name: 'export-links', type: Boolean}
	]

	// Get options from command line
	var options = commandLineArgs(optionDefinitions)
	if(typeof options["input"] == "undefined") {
		throw Error("No input provided");
	}

	if(typeof options["output"] == "undefined") {
		throw Error("No output provided");
	}

	if(typeof options["export-links"] == "undefined") {
		options["export-links"] = false;
	}

  	// Loading file
    console.log("- Loading " + options.input);	
	const data = JSON.parse(fs.readFileSync(options.input).toString());
	let result = [];

	for(let i=0; i<data.length; i++) {
		const item = data[i];

		// Parsing file
		if(item.status < 300) {
			console.log("-- Parsing " + item.url);	
			const simplified_html = await simplifyHTML(item.html, item.url);
			const markdown = await HTML2Markdown(simplified_html)

			if(options["export-links"]) {
				const links = await searchLinks(markdown);
				result.push({
					url: item.url,
					markdown: markdown,
					links: links
				});	
			} else {
				result.push({
					url: item.url,
					markdown: markdown
				});	
			}
		} else {
			console.log("-- Skipping " + item.url + "as the HTTP code is " + item.status);	
		}   
	}

	// Writing output
	console.log("-- Writing to " + options.ouput)
	fs.writeFileSync( options.output, JSON.stringify(result, null, 2));
}

main().catch(console.error);

/*
 * Remaining functions
 */

async function simplifyHTML(data, url) {
	// Load the html data
	// We also set a random base url in this parser. 
	//Later, we will remove this url from our output
	var doc = new JSDOM(data,{
		url: url, 
		referrer: "https://google.com/",
		contentType: "text/html",
		includeNodeLocations: true,
		storageQuota: 10000000
	});

	var article = new Readability(doc.window.document).parse();
 	return article.content;
}

async function HTML2Markdown(html) {
	return turndownService.turndown(html)
}

async function searchLinks(markdown) {
	let result = [];
	const links = await markdown.matchAll(/\[([^\]]*)\]\(([^\)]*)\)/mg)
	await links.forEach(link => {
		url = link[2];

		if(!url.startsWith("http://") && !url.startsWith("https://")){
			return;
		}

		result.push(url);
	});
	return result;
}