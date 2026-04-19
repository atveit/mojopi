# Installation

## Prerequisites

- **pixi** — `curl -fsSL https://pixi.sh/install.sh | bash`
- **macOS Apple Silicon** (`osx-arm64`) or **Linux x86_64** (`linux-64`)
- **Model weights** — Llama-3.1-8B-Instruct-GGUF (Q4_K_M):
  ```bash
  mkdir -p models
  # Download from HuggingFace (requires git-lfs or huggingface-cli)
  huggingface-cli download modularai/Llama-3.1-8B-Instruct-GGUF \
    --local-dir models/
  ```

## From source (recommended)

```bash
git clone https://github.com/atveit/mojopi
cd mojopi/mojopi
pixi install          # resolves Mojo 26.2 + MAX + Python 3.12
pixi run smoke        # verify Mojo→Python→MAX bridge
pixi run test         # run all tests (2–3 min)
```

## Usage

```bash
# One-shot print mode
pixi run run -- -p "Explain list comprehensions in one sentence"

# Read prompt from file
pixi run run -- -p @prompt.txt

# Pipe from stdin
echo "What is a Mojo struct?" | pixi run run -- -p ""

# Streaming JSON output (for editor integrations)
pixi run run -- --mode json -p "Hello"

# Limit tools
pixi run run -- -p "find all Python files" --tools read,find

# Override model
pixi run run -- --model meta-llama/Llama-3.2-1B -p "hi"
```

## Performance notes

- **Apple Silicon (M-series)**: ~15.4 tok/s on CPU (GPU blocked by MAX 26.2 topk kernel)
- **Linux + CUDA**: target > 30 tok/s (not yet validated; NFR gate is Linux CI)
- Cold start (including model load): ~2 s on M-series
- TTFT (model warm): < 150 ms target

## Extensions

Place Python extension files in:
- `~/.pi/agent/extensions/*.py` — global (all projects)
- `.pi/extensions/*.py` — project-local

See [docs/EXTENSIONS.md](EXTENSIONS.md) for the migration guide.
