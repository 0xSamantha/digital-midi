"""Bounded audio snapshots and a mono delay-embedding phase portrait."""
import threading
import numpy as np


class ScopeBuffer:
    def __init__(self, size=4096):
        self.buffer = np.zeros(size, dtype=np.float32)
        self.position = 0
        self.lock = threading.Lock()

    def write(self, samples):
        # The audio callback never waits for the UI; dropping a display block is fine.
        if not self.lock.acquire(blocking=False):
            return
        try:
            data = samples[-len(self.buffer):]
            count = len(data)
            first = min(count, len(self.buffer) - self.position)
            self.buffer[self.position:self.position + first] = data[:first]
            self.buffer[:count - first] = data[first:]
            self.position = (self.position + count) % len(self.buffer)
        finally:
            self.lock.release()

    def read(self):
        with self.lock:
            return np.concatenate((self.buffer[self.position:], self.buffer[:self.position]))


def phase_trace(samples, delay=31, max_points=256):
    values = np.asarray(samples, dtype=np.float32).reshape(-1)[-2048:]
    if len(values) <= delay or not np.isfinite(values).all():
        return np.empty((0, 2), dtype=np.float32), 0.
    peak = float(np.max(np.abs(values)))
    if peak < .0001:
        return np.empty((0, 2), dtype=np.float32), 0.
    # Delay embedding gives a scope-like portrait of the actual mono waveform.
    step = max(1, (len(values) - delay + max_points - 1) // max_points)
    trace = np.column_stack((values[:-delay:step], values[delay::step]))
    trace = np.clip(trace / max(.12, peak) * .84, -1, 1)
    return trace, peak
