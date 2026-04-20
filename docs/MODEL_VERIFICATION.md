# Model verification — empirical tool-calling results

mojopi's ReAct loop expects models to emit tool calls in this exact format:

```
<tool_call>{"name": "tool_name", "arguments": {...}}</tool_call>
```

Different model families have very different levels of support for this
format out of the box. This doc catalogues what actually works on M-series
Metal via mlx-lm + MLX as of **2026-04-20**.

## Headline: Gemma 4 e4b works cleanly

**Model:** `mlx-community/gemma-4-e4b-it-4bit` (2.3 GB 4-bit MLX build of
Gemma 4 with ~4B effective parameters).

**Result:** ✅ Emits `<tool_call>` tags that mojopi's regex extractor
parses on the first turn, without any prompt-engineering hacks.

Sample response when asked to read a file:

```
<|channel>thought
The user wants to know the content of the file /tmp/xyz/hello.txt.
I need to use the `read` tool.<channel|>
<tool_call>{"name": "read", "arguments": {"path": "/tmp/xyz/hello.txt"}}</tool_call>
```

Notes:

- Gemma 4 prefixes its reasoning with `<|channel>thought...<channel|>`.
  mojopi's `strip_thinking_text()` currently handles `<think>`,
  `<thinking>`, `<|thinking|>`, and `` ```thinking ``` — *Gemma's channel
  tag is not yet in the strip list*. The response text with the channel
  tag still passes through the tool-extractor (the regex is scoped to
  `<tool_call>...</tool_call>`), so this is cosmetic for now; a follow-up
  in v1.3 adds the Gemma tag to `thinking.py`.
- TTFT measured at **281 ms** on M2 Max cold-start over Metal (under the
  5 s relaxed gate in `test_run_ttft_under_nfr_target`; warm NFR target
  of 150 ms is achievable once the prompt cache is preheated).

## Preference order (modern-first)

`tests/test_run_integration.py` tries these models in order, picking the
first one found in `~/.cache/huggingface/hub/`:

| # | Model | Size | Notes |
|---|-------|------|-------|
| 1 | `mlx-community/gemma-4-e4b-it-4bit` | 2.3 GB | ✅ **verified** — emits `<tool_call>` tags |
| 2 | `mlx-community/gemma-4-e2b-it-4bit` | 1.2 GB | Smaller Gemma 4 variant, untested |
| 3 | `mlx-community/Qwen2.5-7B-Instruct-4bit` | 4.5 GB | SOTA tool calling, not currently cached |
| 4 | `mlx-community/Qwen3.5-4B-MLX-4bit` | 2.3 GB | Cached; does NOT emit `<tool_call>` tags in plain ChatML (needs Qwen-specific tool prompt) |
| 5 | `mlx-community/Llama-3.2-3B-Instruct-4bit` | 1.8 GB | Cached; Oct 2024 model; tool-capable with explicit format prompting |
| 6 | `mlx-community/Qwen3-0.6B-4bit` | 300 MB | Chat-only fallback; hallucinates tool output |

### What doesn't work (and why)

- **Small Qwen chat models (Qwen3-0.6B):** emit plausible-looking
  plain text but not `<tool_call>` tags. They haven't been fine-tuned
  for structured tool use.
- **Old Llama GGUF via MAX:** `modularai/Llama-3.1-8B-Instruct-GGUF` is
  tool-capable but the MAX 26.2 topk sampler hits an Apple-GPU constraint,
  forcing CPU-only inference at ~15 tok/s. Gemma 4 via MLX gets 50+ tok/s
  on Metal.

## Chat-template portability

Early versions of `test_run_integration.py` hand-rolled Llama-3 ChatML
tokens (`<|begin_of_text|>`, `<|start_header_id|>`, etc.). Gemma 4 uses
a completely different template (`<start_of_turn>user\n...<end_of_turn>`),
so the Llama template produced garbled output when fed to Gemma.

**The fix (shipped):** use `tokenizer.apply_chat_template(messages,
tokenize=False, add_generation_prompt=True)` for all real-model prompts.
This works across Gemma / Qwen / Llama / Mistral without special-casing.

```python
from mlx_lm import load, generate
model, tokenizer = load("mlx-community/gemma-4-e4b-it-4bit")
messages = [{"role": "user", "content": "What does /tmp/foo.txt contain? Use the read tool."}]
prompt = tokenizer.apply_chat_template(
    messages, tokenize=False, add_generation_prompt=True,
)
response = generate(model, tokenizer, prompt, max_tokens=200)
```

## Running the verification yourself

```bash
# 1. Download Gemma 4 e4b (~2.3 GB, ~3 min on typical broadband)
pixi run python -c "from mlx_lm import load; load('mlx-community/gemma-4-e4b-it-4bit')"

# 2. Run the 6 run-tier integration tests
pixi run bash -c "PYTHONPATH=src pytest tests/test_run_integration.py -v -m slow -s"

# 3. Or run the adhoc verifier script
pixi run python scripts/verify_tool_calling.py --model mlx-community/gemma-4-e4b-it-4bit
```

Expected: 6 tests pass in ~16 s once the model is resident in memory.

## What this unlocks

Before this verification, we had:
- 355 unit tests + 38 coverage + 12 walk tests that *mocked* the LLM
- End-to-end tests that only verified the binary didn't crash

After:
- Real proof that a current (2026) MLX-supported open model produces
  tool calls in mojopi's expected format
- A reproducible run-tier gate: if any code change breaks the ReAct loop
  contract, the 6 slow tests fail against real Gemma 4

## v1.3 follow-ups (tracked)

1. Add `<|channel>thought...<channel|>` to `thinking.py` patterns (Gemma family)
2. Add a `scripts/fetch_model.sh` helper that downloads the default Gemma 4
3. Wire `auto_memory_inject` into the real-model test so we can measure
   retrieval's effect on tool-call accuracy
4. Benchmark Gemma 4 e4b throughput (tok/s) on M-series in `scripts/bench.py`
