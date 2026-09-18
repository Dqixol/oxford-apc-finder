#!/bin/bash

# Set current working directory to the current path
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"

# Step 1: For testing purposes I delete all the parsed files already
rm ./markdown/*.md
rm ./markdown/*.txt

# Step 2: Clean the html before sending to LLMs
node main.js --input ./html --output ./markdown --export-links