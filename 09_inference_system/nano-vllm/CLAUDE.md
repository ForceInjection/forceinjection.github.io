# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable) — flash-attn may need a pre-built wheel from GitHub releases
pip install -e .

# Run example (requires Qwen3-0.6B weights)
python example.py

# Run benchmark (256 seqs, 1024/1024 tokens, CUDA Graph on)
python bench.py

# Download model weights (one-time, via modelscope mirror in China)
pip install modelscope
python -c "from modelscope import snapshot_download; snapshot_download('qwen/Qwen3-0.6B', cache_dir='./Qwen3-0.6B/')"
```

**Course exercise scripts** under `docs/llm-inference-visual/scripts/`:

```bash
cd docs/llm-inference-visual/scripts/

# All (GPU needed for L01)
bash run_all.sh --all

# CPU-only (L02-L08)
bash run_all.sh

# Single lesson — model path via argv or NANOVLLM_MODEL_PATH env var
python L03_scheduler.py /path/to/model

# Functional verification (6 test cases)
python verify_nanovllm.py /path/to/model

# Standalone benchmark with argparse
python benchmark.py /path/to/model --num-seqs 64 --max-input 512 --max-output 256
```

No test suite, linter, or type-checker is configured in this repo.

## Architecture

**`LLM` (nanovllm/llm.py) is just a class alias for `LLMEngine`** — the entire public API surface is `LLM.generate(prompts, sampling_params)`, which tokenizes inputs, loops `step()` until all sequences finish, and detokenizes outputs.

### Request lifecycle

1. `LLMEngine.add_request()` tokenizes and wraps the prompt into a `Sequence`, enqueues it in `Scheduler.waiting`.
2. `Scheduler.schedule()` moves sequences through two phases:
   - **Prefill**: takes sequences from `waiting`, allocates KV-cache blocks (with prefix-cache reuse), schedules as many tokens as possible within `max_num_batched_tokens`. First sequence may be chunk-prefilled.
   - **Decode**: pops from `running` in FIFO order, allocates one new block per sequence if needed. Preempts when out of blocks (evicts a running seq back to `waiting`, deallocating its blocks).
3. `ModelRunner.run()` prepares input tensors differently for prefill vs decode, runs the model, and samples next tokens.
4. `Scheduler.postprocess()` writes token outputs back to sequences, hashes completed blocks for prefix caching, and transitions finished sequences to `FINISHED`.

### Key design decisions

- **Thread-local `Context`** (nanovllm/utils/context.py): Scheduling metadata (slot_mapping, block_tables, context_lens, cu_seqlens) is passed to attention layers via a module-level global rather than threading through model forward signatures. This avoids changing the standard Transformer forward interface.
- **Tensor parallelism via multiprocessing**: TP workers are separate processes (spawn context) communicating through NCCL for tensors and `SharedMemory` + `Event` for control. Rank 0 writes method name + pickled args to shared memory; ranks > 0 poll and execute. This is why `Sequence.__getstate__`/`__setstate__` is pickling-aware (only transmits essential fields).
- **CUDA graph** captured for decode at batch sizes [1, 2, 4, 8, 16, 32, ..., max_bs]. Only used when `enforce_eager=False` and `input_ids.size(0) <= 512`.
- **Prefix caching** in `BlockManager`: each filled block is hashed (xxhash) with its prefix hash as a seed, creating a content-addressed lookup. During prefill, `can_allocate()` walks blocks checking hash matches and does reference counting for shared blocks.

### Module map

| Area | Paths | Notes |
|------|-------|-------|
| Public API | `nanovllm/llm.py`, `nanovllm/sampling_params.py`, `nanovllm/__init__.py` | `LLM` = `LLMEngine`; `SamplingParams` |
| Engine (scheduling) | `nanovllm/engine/llm_engine.py`, `nanovllm/engine/scheduler.py`, `nanovllm/engine/sequence.py` | Request lifecycle, prefill/decode loop |
| Engine (execution) | `nanovllm/engine/model_runner.py`, `nanovllm/engine/block_manager.py` | Model invocation, KV-cache allocation |
| Model | `nanovllm/models/qwen3.py` | Only Qwen3 supported; TP-aware from construction |
| Layers | `nanovllm/layers/attention.py`, `nanovllm/layers/linear.py`, `nanovllm/layers/embed_head.py`, `nanovllm/layers/rotary_embedding.py` | FlashAttention, TP linear sharding, RoPE |
| Utilities | `nanovllm/utils/loader.py`, `nanovllm/utils/context.py` | SafeTensors loading, thread-local context |

### Dependencies and constraints

- Python `>=3.10,<3.13`, torch `>=2.4.0`, triton `>=3.0.0`, transformers `>=4.51.0`, `flash-attn`, `xxhash`
- KV-cache block size must be a multiple of 256 (`kvcache_block_size % 256 == 0`)
- Greedy sampling (temperature ≤ 1e-10) is explicitly rejected — minimum is slightly above zero
- Only Qwen3-0.6B model architecture is implemented
- `flash-attn` may fail to `pip install` from source (CPU/memory heavy). Download the pre-built wheel from GitHub releases matching the torch+CUDA version (e.g. `flash_attn-2.8.3+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl`). Use `ghproxy.net` if GitHub is unreachable.
- Course exercise scripts (`docs/llm-inference-visual/scripts/`) are self-contained but share a common `show_source()`/`show_code_block()` helper for displaying nano-vllm source snippets inline. Scripts that need the model accept `sys.argv[1]` or the `NANOVLLM_MODEL_PATH` env var.
- `AGENTS.md` provides further guidance on agent roles, workflows, and documentation conventions for the visual course under `docs/llm-inference-visual/`
