"""GIL hold-time profiler for MAX inference.

Uses Python's sys.settrace to approximate how long MAX holds the GIL
during inference. This is a lightweight sampling approach — not a
full GIL tracer — useful for identifying whether the MAX call path
is a GIL bottleneck.
"""
from __future__ import annotations
import sys
import time
import threading
import contextlib
from dataclasses import dataclass, field
from typing import Generator


@dataclass
class GilProfile:
    wall_time_ms: float = 0.0
    sample_count: int = 0
    estimated_gil_hold_ms: float = 0.0

    @property
    def gil_fraction(self) -> float:
        if self.wall_time_ms == 0:
            return 0.0
        return min(1.0, self.estimated_gil_hold_ms / self.wall_time_ms)


class GilSampler:
    """Samples thread activity to estimate GIL hold time.

    Runs a background thread at SAMPLE_HZ Hz. For each sample, checks if
    the target thread is in a C extension call (heuristic for GIL hold).
    """
    SAMPLE_HZ = 100  # samples per second

    def __init__(self):
        self._running = False
        self._samples: list[bool] = []
        self._thread: threading.Thread | None = None
        self._target_id: int | None = None
        self._lock = threading.Lock()

    def start(self, target_thread_id: int | None = None):
        self._target_id = target_thread_id or threading.current_thread().ident
        self._samples = []
        self._running = True
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def _sample_loop(self):
        interval = 1.0 / self.SAMPLE_HZ
        while self._running:
            frames = sys._current_frames()
            if self._target_id in frames:
                frame = frames[self._target_id]
                # Heuristic: if frame is in a C builtin call chain, GIL is likely held
                in_c_call = frame.f_code.co_filename.startswith("<") or "max" in frame.f_code.co_filename.lower()
                with self._lock:
                    self._samples.append(in_c_call)
            time.sleep(interval)

    def stop(self) -> list[bool]:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        with self._lock:
            return list(self._samples)


@contextlib.contextmanager
def profile_gil(label: str = "") -> Generator[GilProfile, None, None]:
    """Context manager that profiles GIL hold time for a block.

    Example:
        with profile_gil("max_generate") as prof:
            result = pipeline.generate(prompt)
        print(f"GIL fraction: {prof.gil_fraction:.1%}")
    """
    profile = GilProfile()
    sampler = GilSampler()
    sampler.start()
    t0 = time.perf_counter()
    try:
        yield profile
    finally:
        profile.wall_time_ms = (time.perf_counter() - t0) * 1000
        samples = sampler.stop()
        profile.sample_count = len(samples)
        if samples:
            profile.estimated_gil_hold_ms = sum(1 for s in samples if s) / len(samples) * profile.wall_time_ms
        if label:
            print(f"[gil_profiler] {label}: wall={profile.wall_time_ms:.1f}ms "
                  f"~GIL={profile.estimated_gil_hold_ms:.1f}ms ({profile.gil_fraction:.1%})")


def report_metrics(profile: GilProfile) -> dict:
    return {
        "wall_time_ms": round(profile.wall_time_ms, 1),
        "estimated_gil_hold_ms": round(profile.estimated_gil_hold_ms, 1),
        "gil_fraction": round(profile.gil_fraction, 3),
        "sample_count": profile.sample_count,
    }
