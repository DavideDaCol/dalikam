import os
import time
from contextlib import contextmanager


class LoadTimer:
    """Measures and reports wall-clock time for pipeline stages.

    Enabled when the environment variable DALIKAM_BENCHMARK is set to a
    non-empty value.  When disabled, every method is a no-op so the
    overhead is a single ``os.environ.get`` at construction time.
    """

    def __init__(self, title: str = "Load timing") -> None:
        self._enabled = bool(os.environ.get("DALIKAM_BENCHMARK"))
        self._title = title
        self._stages: list[tuple[str, int]] = []
        self._start: int = 0

    @contextmanager
    def measure(self, name: str):
        if not self._enabled:
            yield
            return
        start = time.perf_counter_ns()
        yield
        self._stages.append((name, time.perf_counter_ns() - start))

    def report(self) -> None:
        if not self._enabled or not self._stages:
            return
        total = sum(t for _, t in self._stages)
        pad = max(len(n) for n, _ in self._stages)
        lines = [self._title]
        for name, ns in self._stages:
            lines.append(f"  {name:<{pad}}  {ns / 1e6:8.1f} ms")
        lines.append(f"  {'─' * (pad + 12)}")
        lines.append(f"  {'total':<{pad}}  {total / 1e6:8.1f} ms")
        print("\n".join(lines), flush=True)


_ENABLED = bool(os.environ.get("DALIKAM_BENCHMARK"))


class FrameTracker:
    """Tracks frame times during user interactions to compute FPS metrics.

    Enabled when the environment variable DALIKAM_BENCHMARK is set to a
    non-empty value.  When disabled every method is a no-op.

    Usage:
        1. Call ``begin()`` when an interaction starts (mouse press, slider pressed).
        2. Call ``record_frame()`` from a VTK ``EndRenderEvent`` observer.
        3. Call ``end()`` when the interaction finishes; it returns a dict with
           ``avg_fps``, ``1pct_low_fps``, ``frames`` and ``duration_ms``.
    """

    def __init__(self) -> None:
        self._active = False
        self._intervals: list[int] = []
        self._prev_ns: int = 0

    def begin(self) -> None:
        if not _ENABLED:
            return
        self._active = True
        self._intervals.clear()
        self._prev_ns = 0

    def record_frame(self) -> None:
        if not _ENABLED or not self._active:
            return
        now = time.perf_counter_ns()
        if self._prev_ns > 0:
            self._intervals.append(now - self._prev_ns)
        self._prev_ns = now

    def end(self) -> dict[str, float] | None:
        if not _ENABLED or not self._active:
            return None
        self._active = False
        if len(self._intervals) < 2:
            return None

        total_ns = sum(self._intervals)
        avg_fps = len(self._intervals) / (total_ns / 1e9)

        sorted_iv = sorted(self._intervals, reverse=True)
        n_slow = max(1, len(sorted_iv) // 100)
        slowest_ns = sorted_iv[:n_slow]
        fps_1pct = n_slow / (sum(slowest_ns) / 1e9) if sum(slowest_ns) > 0 else 0.0

        return {
            "avg_fps": avg_fps,
            "1pct_low_fps": fps_1pct,
            "frames": len(self._intervals) + 1,
            "duration_ms": total_ns / 1e6,
        }
