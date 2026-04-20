# Benchmarks

Performance numbers for mojopi across different backends and models.

Measured on Apple M2 Max (MacBook Pro, 12-core CPU, 38-core GPU, 32 GB unified memory).
macOS 26.3, Mojo 0.26.2, MAX 26.2, MLX 0.31.1, mlx-lm 0.31.2.

## Headline

| Backend | Model | TTFT | Throughput | Notes |
|---------|-------|------|------------|-------|
| **MLX Metal** | Qwen3-0.6B-4bit | **114 ms** | **192.7 tok/s** | under NFR TTFT, 6× NFR throughput |
| **MLX Metal** | Qwen3.5-4B-4bit | **298 ms** | **68.6 tok/s** | 2× NFR throughput |
| MAX CPU | Llama-3.1-8B Q4_K_M | 1 950 ms | 15.4 tok/s | the old baseline |

**NFR targets** (PLAN.md §6): TTFT < 150 ms, throughput > 30 tok/s.

MLX Metal on the M2 Max clears both targets on the small-to-mid range. On M3 Ultra
(60-core or 80-core GPU, up to 192 GB unified memory) both numbers scale further —
throughput is GPU-cores-bound and M3 Ultra has 1.5–2× the GPU cores of M2 Max.

## Reproducing

```bash
pixi run python scripts/bench.py --model mlx-community/Qwen3-0.6B-4bit --tokens 64
pixi run python scripts/bench.py --model mlx-community/Qwen3.5-4B-MLX-4bit --tokens 64
pixi run python -c "
import sys; sys.path.insert(0, 'src')
from max_brain.mlx_backend import benchmark_mlx
print(benchmark_mlx(model_repo='mlx-community/Qwen3-0.6B-4bit', max_new_tokens=64))
"
```

## Backend selection

`generate_embedded()` tries backends in this order on Apple Silicon:

1. **MLX Metal** — native Apple GPU via MLX; fastest on M-series
2. **MAX embedded** — MAX's `TextGenerationPipeline` (CPU-pinned on arm64 due to
   MAX 26.2 Apple-GPU `topk` kernel constraint)
3. **MAX subprocess** — fallback; spawns `max generate` CLI

On Linux x86_64 the order is MAX embedded → MAX subprocess; MLX is Apple-only.

## Cold start

First-token time with a cold process (fresh Python import + model load):

| Model | Cold start |
|-------|------------|
| Qwen3-0.6B-4bit (300 MB) | ~1.5 s |
| Qwen3.5-4B-4bit (2.3 GB) | ~3–5 s |
| Llama-3.1-8B GGUF Q4_K_M (4.6 GB) | ~2 s (MAX cached) |

Warm cold start (model in filesystem cache) is much faster — use `pixi run smoke`
to measure on your hardware.

## Model suitability for tool-calling

Not all models emit the `<tool_call>{"name": ..., "arguments": ...}</tool_call>`
format that mojopi's ReAct loop expects. Verified tool-callers:

- ✅ `modularai/Llama-3.1-8B-Instruct-GGUF` (reference; MAX and MLX)
- ✅ `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit`
- ⚠️ `mlx-community/Qwen3-*` — chat-capable, does not reliably emit tool_call XML
- ⚠️ `mlx-community/Qwen3.5-4B-MLX-4bit` — same

For coding-agent workflows use a Llama-3.1-Instruct-class model. Smaller Qwen
models are fine for testing throughput but will hallucinate tool results rather
than call the tools.

## M3 Ultra projection

M3 Ultra has ~2× the GPU cores of M2 Max and 4–6× the memory bandwidth.
Expected performance on M3 Ultra (scaling from M2 Max measurements):

| Model | Expected throughput on M3 Ultra |
|-------|-------------------------------|
| Llama-3.1-8B 4-bit MLX | 60–100 tok/s |
| Llama-3.3-70B 4-bit MLX | 15–25 tok/s |
| Llama-3.3-70B Q8 | 8–15 tok/s |

The unified memory of M3 Ultra (up to 192 GB) also unlocks larger models that
don't fit on discrete GPUs — the 70B-class and even some 120B-class quantized
models should run from a single process.
