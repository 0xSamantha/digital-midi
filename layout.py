"""Shared drawing and hit-testing geometry in a fixed 1200 x 800 canvas."""
from dataclasses import dataclass

WIDTH, HEIGHT = 1200, 800
PAD_NAMES = ['Kick', 'Side stick', 'Snare', 'Clap', 'Low tom', 'Closed hat', 'Mid tom', 'Pedal hat',
             'High tom', 'Open hat', 'Crash', 'Ride', 'Tambourine', 'Cowbell', 'High bongo', 'Low bongo']
PAD_NOTES = [36, 37, 38, 39, 41, 42, 45, 44, 50, 46, 49, 51, 54, 56, 60, 61]

@dataclass
class Zone:
    rect: tuple
    note: int
    channel: int
    label: str
    black: bool = False

    def contains(self, x, y):
        a, b, w, h = self.rect
        return a <= x < a + w and b <= y < b + h


def zones(octave=4):
    pads = [Zone((36 + (i % 4) * 142, 170 + (3 - i // 4) * 73, 130, 62), n, 9, PAD_NAMES[i])
            for i, n in enumerate(PAD_NOTES)]
    keys, blacks = [], []
    for i in range(15):
        offset = (i // 7) * 12 + (0, 2, 4, 5, 7, 9, 11)[i % 7]
        n = 12 * (octave + 1) + offset
        keys.append(Zone((36 + i * 75, 540, 73, 195), n, 0, note_name(n)))
        if i < 14 and i % 7 in (0, 1, 3, 4, 5):
            blacks.append(Zone((36 + (i + 1) * 75 - 23, 540, 44, 119), n + 1, 0, note_name(n + 1), True))
    return pads + keys + blacks


def hit(zones_, x, y):
    return next((z for z in reversed(zones_) if z.contains(x, y)), None)


from controller import note_name
