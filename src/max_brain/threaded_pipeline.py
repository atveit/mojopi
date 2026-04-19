"""Dedicated MAX inference thread to isolate GIL contention.

MAX's TextGenerationPipeline holds the GIL during token generation.
Running it on a dedicated daemon thread means the Mojo caller's Python
interop overhead doesn't compete with MAX's GIL hold time.

Usage:
    pool = MaxInferencePool()
    result = pool.generate(prompt, model_repo, max_new_tokens)
    pool.shutdown()
"""
from __future__ import annotations
import threading
import queue
import time
import contextlib
from typing import Any

from max_brain.pipeline import get_or_create_pipeline


class _InferenceTask:
    def __init__(self, prompt: str, model_repo: str, max_new_tokens: int):
        self.prompt = prompt
        self.model_repo = model_repo
        self.max_new_tokens = max_new_tokens
        self.result: str = ""
        self.error: Exception | None = None
        self.ttft_ms: float = 0.0
        self.throughput_tok_s: float = 0.0
        self._done = threading.Event()

    def wait(self, timeout: float = 300.0) -> str:
        if not self._done.wait(timeout=timeout):
            raise TimeoutError(f"MAX inference timed out after {timeout}s")
        if self.error is not None:
            raise self.error
        return self.result


class MaxInferencePool:
    """Runs MAX inference on a single dedicated background thread."""

    def __init__(self):
        self._task_queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True, name="max-inference")
        self._thread.start()
        self._lock = threading.Lock()
        self._metrics: dict = {"calls": 0, "total_time_ms": 0.0, "total_tokens": 0}

    def _worker(self):
        while True:
            task = self._task_queue.get()
            if task is None:
                break
            t0 = time.perf_counter()
            try:
                pipeline = get_or_create_pipeline(task.model_repo)
                tokens = []
                first_token_time = None

                if hasattr(pipeline, "next"):
                    for tok in pipeline.next(task.prompt):
                        if first_token_time is None:
                            first_token_time = time.perf_counter() - t0
                        tokens.append(str(tok))
                        if len(tokens) >= task.max_new_tokens:
                            break
                elif hasattr(pipeline, "generate"):
                    result = pipeline.generate(task.prompt, max_new_tokens=task.max_new_tokens)
                    first_token_time = time.perf_counter() - t0
                    tokens = [str(result)]
                else:
                    for tok in pipeline(task.prompt):
                        if first_token_time is None:
                            first_token_time = time.perf_counter() - t0
                        tokens.append(str(tok))
                        if len(tokens) >= task.max_new_tokens:
                            break

                total_ms = (time.perf_counter() - t0) * 1000
                task.result = "".join(tokens)
                task.ttft_ms = (first_token_time or (time.perf_counter() - t0)) * 1000
                task.throughput_tok_s = len(tokens) / (total_ms / 1000) if total_ms > 0 else 0

                with self._lock:
                    self._metrics["calls"] += 1
                    self._metrics["total_time_ms"] += total_ms
                    self._metrics["total_tokens"] += len(tokens)

            except Exception as e:
                task.error = e
            finally:
                task._done.set()
                self._task_queue.task_done()

    def generate(self, prompt: str, model_repo: str = "modularai/Llama-3.1-8B-Instruct-GGUF",
                 max_new_tokens: int = 64, timeout: float = 300.0) -> str:
        """Submit inference task and block until complete. Thread-safe."""
        task = _InferenceTask(prompt, model_repo, max_new_tokens)
        self._task_queue.put(task)
        return task.wait(timeout=timeout)

    def get_metrics(self) -> dict:
        with self._lock:
            m = dict(self._metrics)
        m["avg_time_ms"] = m["total_time_ms"] / m["calls"] if m["calls"] > 0 else 0.0
        m["avg_throughput"] = m["total_tokens"] / (m["total_time_ms"] / 1000) if m["total_time_ms"] > 0 else 0.0
        return m

    def shutdown(self):
        """Gracefully stop the worker thread."""
        self._task_queue.put(None)
        self._thread.join(timeout=5.0)


# Module-level singleton (lazy init).
_pool: MaxInferencePool | None = None
_pool_lock = threading.Lock()


def get_inference_pool() -> MaxInferencePool:
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = MaxInferencePool()
    return _pool


def generate_threaded(prompt: str, model_repo: str = "modularai/Llama-3.1-8B-Instruct-GGUF",
                      max_new_tokens: int = 64) -> str:
    """Generate via the singleton MaxInferencePool (dedicated MAX thread)."""
    return get_inference_pool().generate(prompt, model_repo, max_new_tokens)
