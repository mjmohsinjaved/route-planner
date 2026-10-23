"""Collects per-step timings for one log line."""
import time


class Stopwatch:
    def __init__(self):
        self.start = self.last = time.perf_counter()
        self.steps: list[tuple[str, float]] = []

    def lap(self, name: str) -> None:
        now = time.perf_counter()
        self.steps.append((name, now - self.last))
        self.last = now

    def summary(self) -> str:
        parts = ", ".join(f"{name} {secs:.2f}s" for name, secs in self.steps)
        return f"{parts}, total {time.perf_counter() - self.start:.2f}s"
