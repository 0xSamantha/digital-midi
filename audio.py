"""Small polyphonic preview synth; the DAW supplies production instruments."""
import threading
import numpy as np


class Synth:
    samplerate = 48000

    def __init__(self):
        self.voices = {}
        self.lock = threading.Lock()
        self.volume = .18
        self.rng = np.random.default_rng()

    def send(self, kind, channel, note, velocity):
        with self.lock:
            if kind == 'note_on':
                self.voices[channel, note] = [0, velocity / 127, False]
            elif kind == 'note_off' and (channel, note) in self.voices:
                self.voices[channel, note][2] = True
            elif kind == 'control_change':
                self.voices = {k: v for k, v in self.voices.items() if k[0] != channel}

    def callback(self, outdata, frames, timing, status):
        mixed = np.zeros(frames)
        with self.lock:
            for (channel, note), voice in list(self.voices.items()):
                age, velocity, released = voice[:3]
                t = (age + np.arange(frames)) / self.samplerate
                if channel == 9:
                    decay = .12 if note in (42, 44) else .28
                    envelope = np.exp(-t / decay) * np.minimum(t / .002, 1)
                    if note == 36:
                        signal = np.sin(2 * np.pi * (48 * t + 14 * .05 * (1 - np.exp(-t / .05))))
                    elif note in (42, 44, 46, 49, 51, 54):
                        noise = self.rng.uniform(-1, 1, frames)
                        signal = noise - np.roll(noise, 1)
                    else:
                        signal = .5 * self.rng.uniform(-1, 1, frames) + .5 * np.sin(2 * np.pi * 170 * t)
                    mixed += signal * envelope * velocity
                    if t[-1] > 1.8:
                        del self.voices[channel, note]
                        continue
                else:
                    freq = 440 * 2 ** ((note - 69) / 12)
                    envelope = np.minimum(t / .008, 1)
                    if released:
                        envelope *= np.maximum(0, 1 - np.arange(frames) / (self.samplerate * .025))
                        # Store release level between blocks, without discontinuities.
                        envelope *= voice[3] if len(voice) > 3 else 1
                        level = (voice[3] if len(voice) > 3 else 1) * max(0, 1 - frames / (self.samplerate * .025))
                        if len(voice) == 3:
                            voice.append(level)
                        else:
                            voice[3] = level
                        if level < .001:
                            del self.voices[channel, note]
                    signal = np.sin(2 * np.pi * freq * t) + .18 * np.sin(4 * np.pi * freq * t)
                    mixed += signal * envelope * velocity
                voice[0] += frames
        outdata[:, 0] = np.tanh(mixed * self.volume).astype('float32')
