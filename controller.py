"""Pure gesture and note ownership logic, independent of device libraries."""
import math


class Pinch:
    def __init__(self):
        self.ready = False
        self.down = False

    def update(self, points, aspect=4 / 3):
        if points is None or len(points) != 21 or any(not math.isfinite(v) for p in points for v in p):
            self.ready = self.down = False
            return None, False
        p = [(x * aspect, y) for x, y in points]
        palm = math.dist(p[0], p[9])
        if palm < .045:
            self.ready = self.down = False
            return None, False
        ratio = math.dist(p[4], p[8]) / palm
        if ratio > .48:
            self.ready, self.down = True, False
        elif ratio < .26 and self.ready:
            self.down = True
        # Palm anchor remains stable as thumb and index bend.
        return tuple(max(0, min(1, (v - .15) / .7)) for v in points[5]), self.down


class Notes:
    """Reference-count shared notes across independent mouse and hand sources."""
    def __init__(self, send):
        self.send = send
        self.sources = {}

    def set(self, source, target, velocity=100):
        old = self.sources.get(source)
        if old == target:
            return
        if old is not None:
            del self.sources[source]
            if old not in self.sources.values():
                self.send('note_off', *old, 0)
        if target is not None:
            if target not in self.sources.values():
                self.send('note_on', *target, max(1, min(127, int(velocity))))
            self.sources[source] = target

    def panic(self):
        for source in list(self.sources):
            self.set(source, None)
        for channel in (0, 9):
            self.send('control_change', channel, 123, 0)


def note_name(note):
    return ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')[note % 12] + str(note // 12 - 1)
