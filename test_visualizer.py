import unittest
import numpy as np
from visualizer import ScopeBuffer, phase_trace
from audio import Synth


class ScopeTests(unittest.TestCase):
    def test_ring_order_wrap_and_oversized_write(self):
        scope = ScopeBuffer(8)
        scope.write(np.arange(6))
        scope.write(np.arange(6, 12))
        np.testing.assert_array_equal(scope.read(), np.arange(4, 12))
        scope.write(np.arange(20))
        np.testing.assert_array_equal(scope.read(), np.arange(12, 20))

    def test_writer_does_not_wait_for_display_lock(self):
        scope = ScopeBuffer(8)
        scope.lock.acquire()
        try:
            scope.write(np.ones(4))
        finally:
            scope.lock.release()
        self.assertFalse(np.any(scope.read()))

    def test_trace_follows_real_output_and_returns_to_silence(self):
        synth = Synth()
        output = np.zeros((256, 1), dtype=np.float32)
        synth.send('note_on', 0, 60, 100)
        for _ in range(20):
            synth.callback(output, 256, None, None)
        trace, peak = phase_trace(synth.scope.read())
        self.assertGreater(peak, 0)
        self.assertGreater(len(trace), 100)
        self.assertLessEqual(len(trace), 256)
        self.assertTrue(np.isfinite(trace).all())
        self.assertLessEqual(np.max(np.abs(trace)), 1)
        synth.send('control_change', 0, 123, 0)
        for _ in range(20):
            synth.callback(output, 256, None, None)
        trace, peak = phase_trace(synth.scope.read())
        self.assertEqual(len(trace), 0)
        self.assertEqual(peak, 0)
        self.assertEqual(len(phase_trace([float('nan')] * 100)[0]), 0)
