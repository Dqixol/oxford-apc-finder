#!/bin/bash

# Set current working directory to the current path
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"

source venv/bin/activate

# Step 1: remove the old files
# rm -rf ./data
# mkdir ./data

# # Step 2: Scrape the HTML
# python scraper.py > data/raw-html.json

# # Step 3: Clean the html before sending to LLMs
# node main.js --input data/raw-html.json --output data/markdown.json --export-links

# Step 4: Ask a local LLM to parse the text
python parse.py example-data/markdown.json