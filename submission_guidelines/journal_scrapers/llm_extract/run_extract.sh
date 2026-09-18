#!/bin/bash
# SLURM launcher: starts a vLLM OpenAI-compatible server for one model, waits
# for it to finish loading, runs an extraction against it, then tears the
# server down. Without this, client.py/extract_journal.py have nothing to
# actually connect to on the HPC: they were originally written assuming a
# --base-url was already reachable, but nothing in this project starts one
# for llm_extract specifically.
#
# Two modes, chosen by whether PAGE is set:
#   - PAGE unset (default): runs extract_journal.py against every page in
#     page_manifests.py for SLUG, all against this one vLLM server -- looping
#     in-process rather than one SLURM submission per page, since loading a
#     70B model takes ~20 minutes and this journal's manifest has 8 pages
#     (8 separate submissions would mean ~2.5h of pure model-loading before
#     any real work happens).
#   - PAGE (+ SOURCE_URL) set: runs client.py against that one page only --
#     useful for testing/re-running a single page without redoing the rest.
#
# Model choice, conda env, module loads, port-collision avoidance, and the
# `curl` wait-loop are all copied from categorisation/code/
# run_ndns_qwen_generic.sh / run_ndns_llama_generic.sh -- those are the only
# scripts in either project that have actually started these two exact
# models (Qwen2.5-72B-Instruct-AWQ, Meta-Llama-3.3-70B-Instruct-AWQ-INT4) on
# this cluster's vLLM install, across hundreds of real SLURM jobs. Reused
# as-is rather than re-derived, including the `|| true` on the curl poll
# (categorisation/CLAUDE.md: without it, `set -euo pipefail` kills the job in
# ~8 seconds on the first connection-refused poll before vLLM finishes
# loading -- a real bug that cost that project a day to diagnose the first
# time, no reason to re-hit it here).
#
# ---- max-model-len: 32768, NOT categorisation's validated 12000 ----
# categorisation's 12000 was sized for short product-classification prompts
# (~3.4k tokens worst-case per their own measurement). This project's
# longest fetched page so far is BMJ's article-types.md at ~92KB
# (~23k tokens by this project's own len//4 estimate) -- 12000 would 400 on
# it. Raising --max-model-len is confirmed cheap on this cluster's hardware
# (see run_ndns_ranked_test.sh's header comment: vLLM's KV-cache pool comes
# from whatever's left after model weights + an 8192-token profiling pass,
# not from --max-model-len directly, and 80GB+/94GB H100s have millions of
# tokens of spare KV-cache capacity at gpu-memory-utilization 0.90 -- one
# request at 32768 is a rounding error). Not yet measured against a live
# run of THIS project's prompts specifically -- if a future journal's page
# is longer than BMJ's, recheck against this number before assuming it fits.
#
# ---- REQUIRED: pass SLUG, MODEL_KEY at submission time ----
#
# All 8 pages (the default, recommended first run -- Nature's ground truth,
# data_scrapes/1476-4687_nature/latest.json, came from a real bespoke parser
# reading all 8, not a one-time hand-transcription of one page, so this is
# the most rigorously checked baseline to diff against in this project):
#   sbatch --job-name=extract_nature_qwen \
#          --export=ALL,SLUG=1476-4687_nature,MODEL_KEY=qwen \
#          journal_scrapers/llm_extract/run_extract.sh
#
# One page only (e.g. re-running just formatting-guide after a prompt tweak):
#   sbatch --job-name=extract_nature_qwen_fmt \
#          --export=ALL,SLUG=1476-4687_nature,PAGE=formatting-guide,\
#SOURCE_URL=https://www.nature.com/nature/for-authors/formatting-guide,MODEL_KEY=qwen \
#          journal_scrapers/llm_extract/run_extract.sh
#
# PAGES (plural, optional, multi-page mode only) restricts extract_journal.py
# to a comma-separated subset of the manifest, e.g. PAGES=formatting-guide,ai-policy.
#
# MODEL_KEY is "qwen" or "llama" -- see the case statement below for the
# exact served model names (same ones categorisation's launchers use; don't
# guess a different name, the AWQ-quantized weights are what's actually
# cached under $HF_HOME).
# JOURNAL_NAME is optional (both scripts derive one from SLUG if omitted).
# The `--export=ALL,...` prefix matters -- categorisation's CLAUDE.md flags
# that without `ALL,`, --export REPLACES the job's environment instead of
# adding to it, silently dropping everything the login shell normally
# passes through (conda/module setup included).

#SBATCH --account=dtce-schmidt
#SBATCH --qos=schmidt
#SBATCH --time=03:00:00
#SBATCH --clusters=htc
#SBATCH --partition=medium,short
#SBATCH --gres=gpu:1
#SBATCH --constraint=[gpu_mem:80GB|gpu_mem:94GB]
#SBATCH --mem=96G
#SBATCH --job-name=llm_extract
#SBATCH --output=/data/biol-thriving/magd4194/submission_guidelines/data_scrapes/slurm_%x_%j.log
#SBATCH --error=/data/biol-thriving/magd4194/submission_guidelines/data_scrapes/slurm_%x_%j.err

set -euo pipefail

for v in SLUG MODEL_KEY; do
    if [ -z "${!v:-}" ]; then
        echo "ERROR: $v not set. See this script's header comment for the required --export vars."
        exit 1
    fi
done
if [ -n "${PAGE:-}" ] && [ -z "${SOURCE_URL:-}" ]; then
    echo "ERROR: PAGE is set but SOURCE_URL isn't -- single-page mode needs both."
    exit 1
fi
if [ -z "${PAGE:-}" ] && [ -n "${SOURCE_URL:-}" ]; then
    echo "ERROR: SOURCE_URL is set but PAGE isn't -- single-page mode needs both."
    exit 1
fi

echo "=== Job started: $(date) ==="
echo "Node: $(hostname)"
echo "Job: $SLURM_JOB_ID"
echo "SLUG=$SLUG MODEL_KEY=$MODEL_KEY PAGE=${PAGE:-<all pages in manifest>} PAGES=${PAGES:-<unset>}"

# Hardcoded, not derived from the ambient $DATA env var -- see
# categorisation's feedback memory on ARC multi-project accounts.
PROJECT_ROOT=/data/biol-thriving/magd4194

module load Anaconda3
module load CUDA/12.6.0
conda activate $PROJECT_ROOT/envs/vllm-env
export HF_HOME=$PROJECT_ROOT/hf_cache

case "$MODEL_KEY" in
    qwen)  MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ" ;;
    llama) MODEL="ibnzterrell/Meta-Llama-3.3-70B-Instruct-AWQ-INT4" ;;
    *) echo "ERROR: MODEL_KEY must be 'qwen' or 'llama', got '$MODEL_KEY'"; exit 1 ;;
esac

# Derived from SLURM_JOB_ID so a concurrent second run doesn't collide on port.
VLLM_PORT=$((8000 + SLURM_JOB_ID % 1000))

echo ""
echo "Starting vLLM server ($MODEL) on port $VLLM_PORT (max-model-len 32768)..."
python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --tensor-parallel-size 1 \
    --port $VLLM_PORT \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.90 &

VLLM_PID=$!

echo "Waiting for vLLM server to load model..."
for i in $(seq 1 300); do
    RESPONSE=$(curl -s http://localhost:${VLLM_PORT}/v1/models 2>/dev/null || true)
    if echo "$RESPONSE" | grep -q "$MODEL"; then
        echo "vLLM server ready after $((i * 10)) seconds"
        break
    fi
    if [ $i -eq 300 ]; then
        echo "ERROR: vLLM server did not start within 50 minutes (or never served the"
        echo "expected model). Last response from port ${VLLM_PORT}: $RESPONSE"
        kill $VLLM_PID 2>/dev/null
        exit 1
    fi
    sleep 10
done

echo ""
echo "=== Running extraction: $(date) ==="
cd $PROJECT_ROOT/submission_guidelines

if [ -n "${PAGE:-}" ]; then
    echo "Single-page mode: $PAGE"
    python journal_scrapers/llm_extract/client.py \
        --slug "$SLUG" --page "$PAGE" --source-url "$SOURCE_URL" \
        ${JOURNAL_NAME:+--journal-name "$JOURNAL_NAME"} \
        --base-url "http://localhost:${VLLM_PORT}/v1" \
        --model "$MODEL"
else
    echo "Multi-page mode: every page in page_manifests.py for $SLUG"
    python journal_scrapers/llm_extract/extract_journal.py \
        --slug "$SLUG" \
        ${JOURNAL_NAME:+--journal-name "$JOURNAL_NAME"} \
        ${PAGES:+--pages "$PAGES"} \
        --base-url "http://localhost:${VLLM_PORT}/v1" \
        --model "$MODEL"
fi

echo ""
echo "=== Extraction done: $(date) ==="
kill $VLLM_PID
wait $VLLM_PID 2>/dev/null
echo "vLLM server stopped."
