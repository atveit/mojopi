#!/usr/bin/env python3
"""Empirically verify mojopi's tool-calling against a tool-capable MLX model.

Usage:
    pixi run python scripts/verify_tool_calling.py [--model <repo>]

Detects a cached tool-capable model from HF cache and runs a minimal
tool-use prompt. Exits 0 on success, 1 on failure, 2 if no tool-capable
model is available locally (not a real failure — just a skip signal).
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path

# Make src/ importable regardless of how the script is invoked.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


CANDIDATE_MODELS = [
    "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit",
    "mlx-community/Hermes-3-Llama-3.1-8B-4bit",
    "mlx-community/Qwen2.5-7B-Instruct-4bit",
]

HF_CACHE = Path(os.environ.get("HF_HOME", "~/.cache/huggingface")).expanduser() / "hub"

TOOL_PROMPT_SYSTEM = """You are an agent with tools. To call a tool, emit EXACTLY:
<tool_call>{"name": "read", "arguments": {"path": "<path>"}}</tool_call>

Available tools:
- read — read a file. args: {"path": str}
- ls   — list a directory. args: {"path": str}

If a tool call is needed, emit it and nothing else. Otherwise respond in plain text."""

TOOL_PROMPT_USER = "Please read the file /etc/hostname and tell me its contents."


def _model_cached(repo: str) -> bool:
    """Check HF cache for the model's snapshot directory."""
    slug = "models--" + repo.replace("/", "--")
    return (HF_CACHE / slug).exists()


def _find_cached_model() -> str | None:
    for repo in CANDIDATE_MODELS:
        if _model_cached(repo):
            return repo
    return None


def verify_tool_calling(model_repo: str, max_new_tokens: int = 256) -> dict:
    """Run the tool-call smoke test. Returns a result dict."""
    from mlx_lm import load, generate

    model, tokenizer = load(model_repo)

    prompt_parts = [
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n",
        TOOL_PROMPT_SYSTEM,
        "\n<|eot_id|>\n<|start_header_id|>user<|end_header_id|>\n",
        TOOL_PROMPT_USER,
        "\n<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>\n",
    ]
    prompt = "".join(prompt_parts)

    response = generate(model, tokenizer, prompt, max_tokens=max_new_tokens)

    # Check mojopi's extractor
    tool_call_match = re.search(
        r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
        response,
        re.DOTALL,
    )

    extracted = None
    if tool_call_match:
        try:
            extracted = json.loads(tool_call_match.group(1))
        except json.JSONDecodeError:
            extracted = None

    # Also accept bare-JSON fallback (Qwen-style)
    bare_json_match = None
    if extracted is None:
        bare_json_match = re.search(r'\{[^{}]*"name"\s*:\s*"read"[^{}]*\}', response)
        if bare_json_match:
            try:
                extracted = json.loads(bare_json_match.group(0))
            except json.JSONDecodeError:
                pass

    return {
        "model": model_repo,
        "response_excerpt": response[:400],
        "found_tool_call_tag": tool_call_match is not None,
        "found_bare_json": bare_json_match is not None and tool_call_match is None,
        "extracted": extracted,
        "success": extracted is not None and extracted.get("name") == "read",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify mojopi tool-calling empirically.")
    parser.add_argument("--model", help="Override auto-detection with a specific model repo.")
    parser.add_argument("--max-tokens", type=int, default=256)
    args = parser.parse_args()

    model = args.model or _find_cached_model()
    if model is None:
        print("[verify] No tool-capable model in HF cache. Candidates checked:")
        for c in CANDIDATE_MODELS:
            print(f"  - {c}")
        print("\n[verify] Download one with:")
        print(f"  pixi run python -c \"from mlx_lm import load; load('{CANDIDATE_MODELS[0]}')\"")
        return 2

    print(f"[verify] Using model: {model}")
    try:
        result = verify_tool_calling(model, max_new_tokens=args.max_tokens)
    except Exception as e:
        print(f"[verify] ERROR during generation: {e}")
        return 1

    print("\n[verify] Result:")
    print(json.dumps(result, indent=2))

    if result["success"]:
        print("\n[verify] \u2713 Tool-calling verified: mojopi correctly extracted the tool call.")
        return 0
    else:
        print("\n[verify] \u2717 Tool-calling did NOT produce an extractable call.")
        print("       The model may not be tool-trained, or the system prompt needs tuning.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
