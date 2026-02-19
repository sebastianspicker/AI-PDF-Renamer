# Performance – 16GB VRAM + 32GB RAM with Qwen3 8B 128K

This document describes how to get the most out of **16GB GPU VRAM** and **32GB system RAM** when using **Qwen3 8B 128K**.

---

## Pipeline behavior

### PDF extraction (`pdf_extract.py`)

- **CONTEXT_128K_MAX_CONTENT_TOKENS = 120_000** – PDF text is passed through up to ~120K tokens (rest reserved for prompt and response).
- **pdf_to_text(..., max_tokens=...)** – Default 120K; long PDFs are not truncated unnecessarily.

### LLM client (`llm.py`)

- **LocalLLMClient.model = "qwen3:8b"**, **timeout_s = 60.0** – Defaults for 128K requests.
- **CONTEXT_128K_MAX_CHARS_SINGLE = 480_000** – Single request up to ~120K tokens (~480K characters); chunking only for longer documents.
- **CONTEXT_128K_CHUNK_SIZE / OVERLAP** – Chunks of 100K chars with 5K overlap for very long PDFs.
- **max_tokens per request** – Response length is capped (summary 1024, keywords 512, category/final 256 tokens) for faster GPU completion.

### Renamer (`renamer.py`)

- **Prefetch** – The next PDF is extracted in a background thread (ThreadPoolExecutor) while the current one is in the LLM pipeline, overlapping extraction (CPU/RAM) with LLM (GPU).

### Single-shot vs chunking

For Qwen-128K, PDFs whose extracted text stays below ~480k characters (~120k tokens) use a single summary call; only longer documents trigger chunking (100k chars per chunk, 5k overlap). See [RECOGNITION-RATE.md](RECOGNITION-RATE.md) §3.

---

## Tuning options

| Area | Option | Benefit |
|------|--------|---------|
| **Ollama (outside repo)** | Set `OLLAMA_NUM_CTX=131072` at start; optionally `OLLAMA_NUM_GPU=1`, `OLLAMA_MAX_LOADED_MODELS=1` | Full 128K context, one model in VRAM. |
| **CLI** | `--llm-url`, `--llm-model`, `--llm-timeout`, `--max-tokens`; env: `AI_PDF_RENAMER_LLM_*`, `AI_PDF_RENAMER_MAX_TOKENS` | Tune endpoint, model, timeout and extraction cap. |
| **Timeout** | Config/env (default 60s; use 90–120s for very long 128K requests) | Fewer timeouts on large PDFs. |
| **Extraction cap** | RenamerConfig / `AI_PDF_RENAMER_MAX_TOKENS` (default 120000) | Different context profiles (e.g. 32K vs 128K). |
| **Parallel workers** | `--workers N` – N parallel extract+generate_filename tasks; renames applied sequentially | Higher throughput; use with care (LLM rate limits, GPU memory). See RUNBOOK. |

---

## Hardware usage in the pipeline

- **GPU (16GB VRAM):** Qwen3 8B uses ~6–8GB; 128K context increases KV cache. One model, one request—no parallel batching on a single card.
- **RAM (32GB DDR5):** Prefetch holds the next PDF’s text (up to ~480K characters, a few MB); rest for OS, PyMuPDF, Python. No bottleneck.
- **CPU:** PDF extraction (PyMuPDF) runs in parallel with the LLM phase; one extraction thread is enough.

---

## Pre-run checklist

1. Ollama with 128K context: `OLLAMA_NUM_CTX=131072` (or in Modelfile).
2. Model pulled: `ollama pull qwen3:8b`.
3. Optional: Single GPU, single model in memory—`OLLAMA_NUM_GPU=1`, `OLLAMA_MAX_LOADED_MODELS=1` (if you have multiple models/GPUs).

See also [RUNBOOK.md](RUNBOOK.md#ollama-128k-context-qwen3-8b).
