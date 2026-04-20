#!/usr/bin/env python3
"""Real speculative decoding benchmark — 1B draft + 3B main.

Downloads the draft model if missing, runs baseline vs speculative generation
on a fixed prompt, reports throughput + speedup. Writes a JSON result that
can be pasted into docs/BENCHMARKS.md.

Usage:
    pixi run python scripts/bench_speculative.py
    pixi run python scripts/bench_speculative.py --main-repo <repo> --draft-repo <repo>
    pixi run python scripts/bench_speculative.py --dry-run          # skip model load
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

HF_CACHE = Path(os.environ.get("HF_HOME", "~/.cache/huggingface")).expanduser() / "hub"

DEFAULT_MAIN = "mlx-community/Llama-3.2-3B-Instruct-4bit"
DEFAULT_DRAFT = "mlx-community/Llama-3.2-1B-Instruct-4bit"
DEFAULT_PROMPT = "Write a short paragraph explaining what a list comprehension is in Python."


def _model_cached(repo: str) -> bool:
    slug = "models--" + repo.replace("/", "--")
    return (HF_CACHE / slug).exists()


def ensure_cached(repo: str) -> bool:
    """Trigger mlx-lm download; return True if model is available after."""
    if _model_cached(repo):
        return True
    print(f"[bench] {repo} not cached — downloading...")
    try:
        from mlx_lm import load
        t0 = time.time()
        load(repo)
        print(f"[bench] downloaded {repo} in {time.time()-t0:.1f}s")
        return True
    except Exception as e:
        print(f"[bench] failed to download {repo}: {e}")
        return False


def run_benchmark(
    main_repo: str,
    draft_repo: str,
    prompt: str = DEFAULT_PROMPT,
    max_new_tokens: int = 64,
    warmup: bool = True,
    dry_run: bool = False,
) -> dict:
    """Run baseline vs speculative; return metrics."""
    if dry_run:
        return {
            "dry_run": True,
            "main_repo": main_repo,
            "draft_repo": draft_repo,
            "note": "dry run — no model loaded, no generation",
        }

    from max_brain.speculative import benchmark_speculative, clear_cache

    if warmup:
        print(f"[bench] warming up {main_repo} + {draft_repo}...")
        _ = benchmark_speculative(
            prompt="Hello.",
            main_repo=main_repo,
            draft_repo=draft_repo,
            max_new_tokens=4,
        )

    print(f"[bench] real benchmark: prompt='{prompt[:60]}...' tokens={max_new_tokens}")
    result = benchmark_speculative(
        prompt=prompt,
        main_repo=main_repo,
        draft_repo=draft_repo,
        max_new_tokens=max_new_tokens,
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Real speculative-decoding benchmark")
    parser.add_argument("--main-repo", default=DEFAULT_MAIN)
    parser.add_argument("--draft-repo", default=DEFAULT_DRAFT)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-warmup", action="store_true")
    args = parser.parse_args()

    if not args.dry_run:
        for repo in (args.main_repo, args.draft_repo):
            if not ensure_cached(repo):
                print(f"[bench] abort — {repo} unavailable", file=sys.stderr)
                return 2

    result = run_benchmark(
        main_repo=args.main_repo,
        draft_repo=args.draft_repo,
        prompt=args.prompt,
        max_new_tokens=args.max_new_tokens,
        warmup=not args.no_warmup,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print()
    print("Speculative decoding benchmark")
    print("=" * 60)
    print(f"main  : {result.get('main_model', args.main_repo)}")
    print(f"draft : {result.get('draft_model', args.draft_repo)}")
    if result.get("dry_run"):
        print("(dry run — no generation performed)")
        return 0
    baseline = result.get("baseline", {})
    spec = result.get("speculative", {})
    print()
    print(f"baseline      : {baseline.get('throughput_tok_s', '?')} tok/s  "
          f"(TTFT {baseline.get('ttft_ms', '?')} ms, {baseline.get('total_tokens', '?')} tokens)")
    print(f"speculative   : {spec.get('throughput_tok_s', '?')} tok/s  "
          f"(TTFT {spec.get('ttft_ms', '?')} ms, {spec.get('total_tokens', '?')} tokens)")
    print(f"speedup       : {result.get('speedup', '?')}x")
    if result.get("note"):
        print(f"note          : {result['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
