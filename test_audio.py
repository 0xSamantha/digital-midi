import unittest
import numpy as np
from audio import Synth


class AudioTests(unittest.TestCase):
    def test_polyphony_release_and_panic(self):
        synth = Synth()
        block = np.zeros((256, 1), dtype='float32')
        synth.send('note_on', 0, 60, 100)
        synth.send('note_on', 0, 64, 100)
        synth.send('note_on', 9, 36, 100)
        synth.callback(block, 256, None, None)
        self.assertTrue(np.isfinite(block).all())
        self.assertGreater(np.max(np.abs(block)), 0)
        self.assertLessEqual(np.max(np.abs(block)), 1)
        synth.send('note_off', 0, 60, 0)
        for _ in range(100):
            synth.callback(block, 256, None, None)
        self.assertNotIn((0, 60), synth.voices)
        self.assertIn((0, 64), synth.voices)
        synth.send('control_change', 0, 123, 0)
        synth.send('control_change', 9, 123, 0)
        synth.callback(block, 256, None, None)
        self.assertFalse(np.any(block))

    def test_percussion_decays_without_note_off(self):
        synth = Synth()
        synth.send('note_on', 9, 42, 127)
        block = np.zeros((480, 1), dtype='float32')
        for _ in range(200):
            synth.callback(block, 480, None, None)
        self.assertFalse(synth.voices)
        self.assertFalse(np.any(block))
