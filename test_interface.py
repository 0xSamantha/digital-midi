"""Qt interaction checks. Run with QT_QPA_PLATFORM=offscreen on headless systems."""
import unittest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from interface import InstrumentWindow
from monitor import PerformanceMonitor, camera_crop
from layout import zones
import threading
import time
import numpy as np
from PySide6.QtGui import QImage, QColor

APP = QApplication.instance() or QApplication([])
APP.setStyle('Fusion')


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.window = InstrumentWindow(lambda *e: self.events.append(e), mouse_only=True, audio=False)
        self.window.show()
        APP.processEvents()

    def tearDown(self):
        self.window.close()
        APP.processEvents()

    def test_mouse_black_key_priority_and_release(self):
        QTest.mousePress(self.window, Qt.MouseButton.LeftButton, pos=QPoint(110, 610))
        self.assertEqual(self.events[-1], ('note_on', 0, 61, 100))
        QTest.mouseRelease(self.window, Qt.MouseButton.LeftButton, pos=QPoint(110, 610))
        self.assertEqual(self.events[-1], ('note_off', 0, 61, 0))

    def test_resize_preserves_hit_testing(self):
        self.window.resize(1000, 720)
        APP.processEvents()
        point = QPoint(round(self.window.offset.x() + 55 * self.window.scale),
                       round(self.window.offset.y() + 750 * self.window.scale))
        QTest.mousePress(self.window, Qt.MouseButton.LeftButton, pos=point)
        self.assertEqual(self.events[-1], ('note_on', 0, 60, 100))
        QTest.mouseRelease(self.window, Qt.MouseButton.LeftButton, pos=point)

    def test_computer_keys_release_even_after_focus_changes(self):
        QTest.keyPress(self.window, Qt.Key.Key_A)
        self.assertIn(('note_on', 0, 60, 100), self.events)
        self.window.slider.setFocus()
        QTest.keyRelease(self.window.slider, Qt.Key.Key_A)
        self.assertFalse(self.window.notes.sources)
        self.assertIn(('note_off', 0, 60, 0), self.events)

    def test_pause_octave_and_panic(self):
        QTest.keyPress(self.window, Qt.Key.Key_A)
        self.window.toggle_pause()
        self.assertFalse(self.window.notes.sources)
        self.assertTrue(self.window.paused)
        QTest.keyPress(self.window, Qt.Key.Key_S)
        self.assertFalse(self.window.notes.sources)
        self.window.toggle_pause()
        self.window.change_octave(1)
        QTest.keyPress(self.window, Qt.Key.Key_A)
        self.assertEqual(self.events[-1], ('note_on', 0, 72, 100))
        QTest.keyPress(self.window, Qt.Key.Key_P)
        self.assertFalse(self.window.notes.sources)

    def test_deactivation_releases_and_blocks_hand_notes(self):
        self.window.notes.set('Left', (0, 60))
        self.window.application_state(Qt.ApplicationState.ApplicationInactive)
        self.assertFalse(self.window.notes.sources)
        points = [(.5, .6)] * 21
        points[0], points[9] = (.5, .8), (.5, .5)
        points[4], points[8] = (.3, .5), (.6, .5)
        self.window.update_hands({'Left': points}, 4 / 3)
        points[8] = (.31, .5)
        self.window.update_hands({'Left': points}, 4 / 3)
        self.assertFalse(self.window.notes.sources)

    def test_diagnostics_separate_and_render_states(self):
        self.assertFalse(self.window.diagnostics.isVisible())
        self.assertTrue(self.window.grab().save('/private/tmp/digital-midi-default.png'))
        self.window.toggle_diagnostics()
        self.assertTrue(self.window.diagnostics.isVisible())
        self.assertTrue(self.window.diagnostics.grab().save('/private/tmp/digital-midi-diagnostics.png'))
        self.window.diagnostics.close()
        self.window.notes.set('test', (0, 60))
        self.window.notes.set('pad', (9, 36))
        self.assertTrue(self.window.grab().save('/private/tmp/digital-midi-active.png'))
        self.window.resize(1000, 672)
        APP.processEvents()
        self.assertTrue(self.window.grab().save('/private/tmp/digital-midi-small.png'))
        self.assertEqual(len([z for z in zones() if z.channel == 0]), 25)


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        class FakeTracker:
            preview = threading.Event()
            debug = threading.Event()
            latest = None
            def take(self):
                sample, self.latest = self.latest, None
                return sample, ''
            def isRunning(self):
                return False
        self.tracker = FakeTracker()
        self.window = InstrumentWindow(lambda *e: self.events.append(e), self.tracker, scope_source=lambda: np.zeros(4096))
        self.window.show()
        APP.processEvents()

    def tearDown(self):
        self.window.close()
        APP.processEvents()

    def test_switch_keeps_notes_and_camera_is_clean_feed(self):
        self.assertEqual(self.window.monitor.mode, 'camera')
        self.assertTrue(self.tracker.preview.is_set())
        self.window.notes.set('held', (0, 60))
        previous = list(self.events)
        QTest.mouseClick(self.window.scope_button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.window.monitor.mode, 'scope')
        self.assertFalse(self.tracker.preview.is_set())
        self.assertEqual(self.events, previous)
        QTest.keyClick(self.window, Qt.Key.Key_V)
        self.assertEqual(self.window.monitor.mode, 'camera')
        clean = QImage(320, 240, QImage.Format.Format_RGB32); clean.fill(QColor('#355D56'))
        debug = QImage(320, 240, QImage.Format.Format_RGB32); debug.fill(QColor('#FF681F'))
        self.tracker.latest = ({}, 4/3, clean, debug, 30., time.monotonic())
        self.window.poll()
        self.assertEqual(self.window.monitor.image.pixelColor(0, 0), QColor('#355D56'))
        self.assertFalse(self.window.diagnostics.isVisible())
        self.window.grab().save('/private/tmp/digital-midi-camera.png')
        self.window.set_monitor_mode('scope')
        t = np.arange(4096) / 48000
        self.window.monitor.set_audio(.17 * np.sin(2 * np.pi * 220 * t) + .05 * np.sin(2 * np.pi * 440 * t))
        self.window.grab().save('/private/tmp/digital-midi-scope.png')
        self.window.resize(1000, 672); APP.processEvents()
        self.window.grab().save('/private/tmp/digital-midi-monitor-small.png')

    def test_stalled_camera_is_not_shown_as_live(self):
        image = QImage(320, 240, QImage.Format.Format_RGB32)
        self.window.monitor.image = image
        self.window.last_frame = time.monotonic() - 1
        self.window.poll()
        self.assertIsNone(self.window.monitor.image)


class MonitorPerformanceTests(unittest.TestCase):
    def test_camera_covers_wide_and_tall_screens_without_black_bars(self):
        for source, target in (((640, 480), (360, 156)), ((1280, 720), (200, 300))):
            crop = camera_crop(*source, *target)
            self.assertAlmostEqual(crop.width() / crop.height(), target[0] / target[1])
            self.assertGreaterEqual(crop.left(), 0)
            self.assertGreaterEqual(crop.top(), 0)
            self.assertLessEqual(crop.right(), source[0])
            self.assertLessEqual(crop.bottom(), source[1])
        monitor = PerformanceMonitor()
        monitor.resize(360, 156)
        image = QImage(640, 480, QImage.Format.Format_RGB32); image.fill(QColor('#355D56'))
        monitor.mode = 'camera'; monitor.image = image
        monitor.show(); APP.processEvents()
        painted = monitor.grab().toImage()
        self.assertEqual(painted.pixelColor(3, 78), QColor('#355D56'))
        self.assertEqual(painted.pixelColor(356, 78), QColor('#355D56'))
        monitor.close()

    def test_monitor_repaint_does_not_repaint_parent_and_cursor_reuses_face(self):
        window = InstrumentWindow(lambda *e: None, mouse_only=True)
        window.show(); APP.processEvents()
        paints = []
        original = window.paintEvent
        def paint(event):
            paints.append(True)
            original(event)
        window.paintEvent = paint
        window.monitor.repaint(); APP.processEvents()
        self.assertFalse(paints)
        window.cursors = {'Left': (300, 600, False)}
        window.repaint(); APP.processEvents()
        face = window._face_cache.cacheKey()
        window.cursors['Left'] = (310, 610, False)
        window.repaint(); APP.processEvents()
        self.assertEqual(window._face_cache.cacheKey(), face)
        window.notes.set('test', (0, 60))
        window.repaint(); APP.processEvents()
        self.assertNotEqual(window._face_cache.cacheKey(), face)
        window.close()
