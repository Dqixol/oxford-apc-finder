all:
	APC_FIXTURES=1 .venv/bin/python pipeline/run_all.py
run:
	.venv/bin/python -m http.server 8765 -d _site
clean:
	rm -rf _site