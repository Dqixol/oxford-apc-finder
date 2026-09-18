# 
# Constants
# 

# This is my personal API key, use with discretion
API_KEY = "fc-84ba894156304316afdaa8993c4d36c5"

URLS = [
    "https://msp.org/gt/about/journal/submissions.html",
    "https://www.sciencedirect.com/journal/advances-in-mathematics/publish/guide-for-authors",
    "https://academic.oup.com/eurheartj/pages/General_Instructions",
    "https://www.lms.ac.uk/publications/jlms#submit-to-the-journal",
    "https://link.springer.com/brands/springer/journal-policies",
    "https://www.pnas.org/author-center/submitting-your-manuscript",
    "https://www.thelancet.com/submission-guidelines",
    "https://publishingsupport.iopscience.iop.org/journals/classical-and-quantum-gravity/"
]

# 
# Libraries
# 
import sys
import json
from firecrawl import Firecrawl
firecrawl = Firecrawl(api_key=API_KEY)


# Or synchronous: starts the batch and waits for completion
job = firecrawl.batch_scrape(URLS, parsers=["pdf"],formats=["rawHtml"], poll_interval=2, wait_timeout=120)

result = [];
for pages in job.data:
    item = {
        "status": pages.metadata.status_code,
        "url": pages.metadata.url,
        "html": pages.raw_html
    }
    result.append(item)

json.dump(result, sys.stdout, ensure_ascii=False, indent=4)
