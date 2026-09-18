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

	var options = commandLineArgs(optionDefinitions)
	if(typeof options["export-links"] == "undefined") {
		options["export-links"] = false;
	}

	// Go through all files in the input folder
	fs.readdir(options.input, (err, files) => {
	  files.forEach(async file => {
	  	// Check extension
	  	if(!file.match(/\.html?$/i)) {
	  		return;
	  	}

	  	const basename = file.match(/^(.*)\.html?$/i)[1];

	  	if (!fs.existsSync(options.input + "/" + basename + ".txt")) {
			  throw Error ("Cannot find " + basename + ".txt. This file must contain the origional url where the html is from")
			}

	  	// Loading file
      console.log("- Loading " + basename);	
	    const raw_html = fs.readFileSync(options.input + '/' + file).toString();
	    const url = fs.readFileSync(options.input + '/' + basename + ".txt").toString().trim();


			// Parsing file
	    console.log("-- Parsing " + file);	
			const simplified_html = await simplifyHTML(raw_html, url);
			const markdown = await HTML2Markdown(simplified_html)

			let links = "";
			if(options["export-links"]) {
				links = await searchLinks(markdown);
			}

			// Writing output
			console.log("-- Writing to " + basename + ".md")
			fs.writeFileSync( options.output + '/' + basename + ".md", markdown)

			if(options["export-links"]) {
				console.log("-- Writing to " + basename + ".txt")
				fs.writeFileSync( options.output + '/' + basename + ".txt", links)
			}
	  });
	});
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
	let result = "";
	const links = await markdown.matchAll(/\[([^\]]*)\]\(([^\)]*)\)/mg)
	await links.forEach(link => {
		url = link[2];

		if(!url.startsWith("http://") && !url.startsWith("https://")){
			return;
		}

		result += url + "\n";
	});
	return result;
}