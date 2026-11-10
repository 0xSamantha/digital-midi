import types
import unittest
from unittest.mock import patch, Mock
import numpy as np
from tracking import Tracker, LatestCamera
import time


class TrackingPreviewTests(unittest.TestCase):
    def test_self_view_is_copied_before_diagnostic_overlays(self):
        cap = Mock()
        cap.read.return_value = True, np.zeros((120, 160, 3), dtype=np.uint8)
        landmarks = object()
        info = types.SimpleNamespace(label='Left', score=.9)
        points = [types.SimpleNamespace(x=.5, y=.5) for _ in range(21)]
        landmarks = types.SimpleNamespace(landmark=points)
        result = types.SimpleNamespace(multi_hand_landmarks=[landmarks],
                                       multi_handedness=[types.SimpleNamespace(classification=[info])])
        hands = Mock()
        hands.process.return_value = result
        manager = Mock()
        manager.__enter__ = Mock(return_value=hands)
        manager.__exit__ = Mock(return_value=False)
        def draw(frame, *args):
            frame[:] = 255
        solutions = types.SimpleNamespace(hands=types.SimpleNamespace(Hands=lambda **kw: manager, HAND_CONNECTIONS=[]),
                                          drawing_utils=types.SimpleNamespace(draw_landmarks=draw))
        reader = Mock()
        reader.take.return_value = (np.zeros((120, 160, 3), dtype=np.uint8), 123.)
        tracker = Tracker()
        tracker.preview.set()
        tracker.debug.set()
        with patch.dict('sys.modules', {'mediapipe': types.SimpleNamespace(solutions=solutions)}), \
             patch('camera.open_camera', return_value=cap), \
             patch('tracking.LatestCamera', return_value=reader), \
             patch.object(tracker, 'isInterruptionRequested', side_effect=[False, True]):
            tracker.run()
        sample, error = tracker.take()
        self.assertEqual(error, '')
        found, aspect, clean, debug, fps, timestamp = sample
        self.assertIn('Left', found)
        self.assertEqual(clean.pixelColor(0, 0).red(), 0)
        self.assertEqual(debug.pixelColor(0, 0).red(), 255)
        self.assertAlmostEqual(clean.width() / clean.height(), 4 / 3)
        reader.close.assert_called_once()
        self.assertEqual(timestamp, 123.)


class CaptureTests(unittest.TestCase):
    def test_slow_consumer_receives_newest_frame_without_backlog(self):
        capture = LatestCamera(Mock())
        first = np.zeros((2, 2, 3), dtype=np.uint8)
        newest = np.ones((2, 2, 3), dtype=np.uint8)
        capture.publish(first, 1.)
        capture.publish(newest, 2.)
        frame, timestamp = capture.take()
        self.assertIs(frame, newest)
        self.assertEqual(timestamp, 2.)
        self.assertIsNone(capture.take(timeout=0))

    def test_capture_failure_releases_device_and_reports_error(self):
        cap = Mock()
        cap.read.return_value = (False, None)
        capture = LatestCamera(cap)
        capture.run()
        with self.assertRaisesRegex(RuntimeError, 'Camera disconnected'):
            capture.take(timeout=0)
        cap.release.assert_called_once()
