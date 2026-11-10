import unittest
from controller import Notes, Pinch
from layout import zones, hit


class NotesTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.notes = Notes(lambda *event: self.events.append(event))

    def test_shared_note_waits_for_last_source(self):
        self.notes.set('Left', (0, 60))
        self.notes.set('mouse', (0, 60))
        self.notes.set('Left', None)
        self.assertEqual(self.events, [('note_on', 0, 60, 100)])
        self.notes.set('mouse', None)
        self.assertEqual(self.events[-1], ('note_off', 0, 60, 0))

    def test_slide_and_panic_release_channels(self):
        self.notes.set('Left', (0, 60))
        self.notes.set('Left', (9, 36))
        self.assertEqual(self.events[1:3], [('note_off', 0, 60, 0), ('note_on', 9, 36, 100)])
        self.notes.panic()
        self.assertFalse(self.notes.sources)
        self.assertIn(('note_off', 9, 36, 0), self.events)
        self.assertEqual(self.events[-2:], [('control_change', 0, 123, 0), ('control_change', 9, 123, 0)])

    def test_channels_and_velocity(self):
        self.notes.set('a', (0, 60), 200)
        self.notes.set('b', (9, 60), 0)
        self.assertEqual(self.events, [('note_on', 0, 60, 127), ('note_on', 9, 60, 1)])


class GestureTests(unittest.TestCase):
    def points(self, distance):
        p = [(.5, .6)] * 21
        p[0], p[9] = (.5, .8), (.5, .5)
        p[4], p[8] = (.4, .5), (.4 + distance, .5)
        return p

    def test_requires_open_and_resets_on_loss(self):
        pinch = Pinch()
        self.assertFalse(pinch.update(self.points(.02))[1])
        self.assertFalse(pinch.update(self.points(.2))[1])
        self.assertTrue(pinch.update(self.points(.02))[1])
        self.assertFalse(pinch.update(None)[1])
        self.assertFalse(pinch.update(self.points(.02))[1])

    def test_hysteresis_and_invalid_points(self):
        pinch = Pinch()
        pinch.update(self.points(.2))
        self.assertTrue(pinch.update(self.points(.02))[1])
        self.assertTrue(pinch.update(self.points(.08))[1])
        self.assertFalse(pinch.update(self.points(.2))[1])
        p = self.points(.02)
        p[0] = (float('nan'), 0)
        self.assertEqual(pinch.update(p), (None, False))


class GeometryTests(unittest.TestCase):
    def test_black_keys_and_bounds(self):
        layout = zones()
        self.assertEqual(hit(layout, 110, 610).note, 61)
        self.assertEqual(hit(layout, 100, 750).note, 60)
        self.assertIsNone(hit(layout, 0, 0))
        self.assertEqual(len([z for z in layout if z.channel == 0]), 25)
        self.assertEqual(len([z for z in layout if z.channel == 9]), 16)
        for octave in (0, 7):
            self.assertTrue(all(0 <= z.note <= 127 for z in zones(octave)))


if __name__ == '__main__':
    unittest.main()
