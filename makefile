all:
	APC_FIXTURES=1 .venv/bin/python pipeline/run_all.py
run:
	.venv/bin/python pipeline/serve.py 8765
clean:
	rm -rf _site