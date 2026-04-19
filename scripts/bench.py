#!/usr/bin/env python3
"""mojopi benchmark runner — TTFT, throughput, RSS, cold start.

Usage:
  PYTHONPATH=src python scripts/bench.py [--model <repo>] [--tokens N] [--runs N] [--json]

Outputs a summary table (or JSON with --json).
Requires model weights; skip with --dry-run to just verify harness works.
"""
import argparse
import json
import os
import sys
import time
import resource
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

DEFAULT_MODEL = "modularai/Llama-3.1-8B-Instruct-GGUF"
DEFAULT_TOKENS = 64
DEFAULT_RUNS = 3
BENCH_PROMPT = "Explain the difference between a list and a tuple in Python in one sentence."


def measure_rss_mb() -> float:
    """Resident set size in MB (excl. shared libs, best-effort)."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # ru_maxrss is bytes on Linux, pages on macOS
    if sys.platform == "darwin":
        return usage.ru_maxrss / (1024 * 1024)
    return usage.ru_maxrss / 1024


def run_ttft_benchmark(pipeline, prompt: str, max_new_tokens: int) -> dict:
    """Measure time-to-first-token using the embedded pipeline."""
    t0 = time.perf_counter()
    first_token_time = None
    tokens = []

    if hasattr(pipeline, "next"):
        for tok in pipeline.next(prompt):
            if first_token_time is None:
                first_token_time = time.perf_counter() - t0
            tokens.append(str(tok))
            if len(tokens) >= max_new_tokens:
                break
    elif hasattr(pipeline, "generate"):
        result = pipeline.generate(prompt, max_new_tokens=max_new_tokens)
        first_token_time = time.perf_counter() - t0
        tokens = list(str(result))
    else:
        for tok in pipeline(prompt):
            if first_token_time is None:
                first_token_time = time.perf_counter() - t0
            tokens.append(str(tok))
            if len(tokens) >= max_new_tokens:
                break

    total_time = time.perf_counter() - t0
    n_tokens = len(tokens)
    throughput = n_tokens / total_time if total_time > 0 else 0

    return {
        "ttft_ms": round((first_token_time or total_time) * 1000, 1),
        "throughput_tok_s": round(throughput, 1),
        "total_tokens": n_tokens,
        "total_time_s": round(total_time, 3),
    }


def run_cold_start_benchmark(model: str, max_new_tokens: int) -> dict:
    """Measure cold-start time via subprocess (fresh process = no cached pipeline)."""
    prompt = BENCH_PROMPT
    cmd = [
        sys.executable, "-c",
        f"""
import sys, time, os
sys.path.insert(0, 'src')
os.environ['PYTHONPATH'] = 'src'
t0 = time.perf_counter()
from max_brain.pipeline import get_or_create_pipeline
p = get_or_create_pipeline('{model}')
t1 = time.perf_counter()
print(f'COLD_START_MS={{round((t1-t0)*1000, 1)}}')
"""
    ]
    t0 = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    total = time.perf_counter() - t0

    cold_start_ms = None
    for line in result.stdout.splitlines():
        if line.startswith("COLD_START_MS="):
            try:
                cold_start_ms = float(line.split("=")[1])
            except ValueError:
                pass

    return {
        "cold_start_ms": cold_start_ms or round(total * 1000, 1),
        "subprocess_exit_code": result.returncode,
    }


def bench(model: str, max_new_tokens: int, runs: int, dry_run: bool) -> dict:
    if dry_run:
        return {
            "model": model,
            "dry_run": True,
            "ttft_ms": None,
            "throughput_tok_s": None,
            "rss_mb": round(measure_rss_mb(), 1),
            "cold_start_ms": None,
        }

    from max_brain.pipeline import get_or_create_pipeline

    rss_before = measure_rss_mb()
    pipeline = get_or_create_pipeline(model)
    rss_after = measure_rss_mb()

    results = []
    for _ in range(runs):
        r = run_ttft_benchmark(pipeline, BENCH_PROMPT, max_new_tokens)
        results.append(r)

    avg_ttft = sum(r["ttft_ms"] for r in results) / runs
    avg_tput = sum(r["throughput_tok_s"] for r in results) / runs

    cold = run_cold_start_benchmark(model, max_new_tokens)

    return {
        "model": model,
        "runs": runs,
        "ttft_ms": round(avg_ttft, 1),
        "throughput_tok_s": round(avg_tput, 1),
        "rss_before_mb": round(rss_before, 1),
        "rss_after_model_load_mb": round(rss_after, 1),
        "cold_start_ms": cold["cold_start_ms"],
    }


def main():
    parser = argparse.ArgumentParser(description="mojopi benchmark suite")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--tokens", type=int, default=DEFAULT_TOKENS)
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="skip model load; just check harness")
    args = parser.parse_args()

    results = bench(args.model, args.tokens, args.runs, args.dry_run)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\nmojopi benchmark results")
        print(f"  model:       {results['model']}")
        if results.get("dry_run"):
            print(f"  [dry-run mode — model not loaded]")
            print(f"  rss:         {results['rss_mb']} MB")
        else:
            print(f"  runs:        {results['runs']}")
            print(f"  TTFT:        {results['ttft_ms']} ms")
            print(f"  throughput:  {results['throughput_tok_s']} tok/s")
            print(f"  RSS (model): {results['rss_after_model_load_mb']} MB")
            print(f"  cold start:  {results['cold_start_ms']} ms")
        print()

        # NFR targets (from PLAN.md §6)
        if not results.get("dry_run"):
            nfr = {"TTFT < 150 ms": results["ttft_ms"] < 150,
                   "Throughput > 30 tok/s": results["throughput_tok_s"] > 30,
                   "RSS < 100 MB (excl. weights)": results["rss_before_mb"] < 100,
                   "Cold start < 50 ms (excl. model load)": False}  # not measured here
            print("  NFR gate:")
            for name, ok in nfr.items():
                print(f"    {'✓' if ok else '✗'} {name}")
        print()


if __name__ == "__main__":
    main()
