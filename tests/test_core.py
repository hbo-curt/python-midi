from __future__ import division
from tests.data import mary_test
import unittest
import midi


class TestIO(unittest.TestCase):
    def setUp(self):
        self.pattern=midi.read_midifile("./data/overlap.mid")
        self.assertEqual(self.pattern.resolution, 480)
        self.assertEqual(len(self.pattern), 1)

    def test_read(self):
        self.assertEqual(len(filter(lambda e: isinstance(e, midi.SetTempoEvent), self.pattern[0])), 1)
        self.assertEqual(len(filter(lambda e: isinstance(e, midi.NoteOffEvent), self.pattern[0])), 0)
        self.assertEqual(len(filter(lambda e: isinstance(e, midi.NoteOnEvent), self.pattern[0])), 4)

    def test_track_text(self):
        self.assertEqual(self.pattern[0].get_text(midi.TrackNameEvent.metacommand), "Classic Electric Piano")
        self.assertEqual(self.pattern[0].get_text(midi.InstrumentNameEvent.metacommand), "curt")
        self.assertEqual(self.pattern[0].get_text(-1, "literal"), "literal")
        self.assertEqual(self.pattern[0].get_text(-1, lambda: "expression"), "expression")

class TestTickConverter(unittest.TestCase):
    def test_convert(self):
        # tempo.mid:
        #   - resolution: 480
        #   - tempos: [{0: 30}, {480: 60}, {960: 90}, {1440, 120}]
        pattern=midi.read_midifile("./data/tempo.mid")
        converter=pattern.get_tick_converter()
        self.assertEqual(pattern.resolution, 480)
        self.assertEqual(len(filter(lambda e: isinstance(e, midi.SetTempoEvent), pattern[0])), 4)
        self.assertEqual(converter.offset_to_seconds(480*0), 0)
        self.assertEqual(converter.offset_to_seconds(480*4), 60/30*4)
        self.assertAlmostEqual(converter.offset_to_seconds(480*8), 60/30*4+60/60*4, places=5)
        self.assertAlmostEqual(converter.offset_to_seconds(480*12), 60/30*4+60/60*4+60/90*4, places=5)
        self.assertAlmostEqual(converter.offset_to_seconds(480*16), 60/30*4+60/60*4+60/90*4+60/120*4, places=5)
        self.assertAlmostEqual(converter.offset_to_seconds(480*10), 60/30*4+60/60*4+60/90*2, places=5)


class TestMIDI(unittest.TestCase):
    def test_varlen(self):
        maxval = 0x0FFFFFFF
        for inval in xrange(0, maxval, maxval / 1000):
            datum = midi.write_varlen(inval)
            outval = midi.read_varlen(iter(datum))
            self.assertEqual(inval, outval)

    def test_mary(self):
        midi.write_midifile("./data/mary.mid", mary_test.MARY_MIDI)
        pattern1 = midi.read_midifile("./data/mary.mid")
        midi.write_midifile("./data/mary.mid", pattern1)
        pattern2 = midi.read_midifile("./data/mary.mid")
        self.assertEqual(len(pattern1), len(pattern2))
        for track_idx in range(len(pattern1)):
            self.assertEqual(len(pattern1[track_idx]), len(pattern2[track_idx]))
            for event_idx in range(len(pattern1[track_idx])):
                event1 = pattern1[track_idx][event_idx]
                event2 = pattern2[track_idx][event_idx]
                self.assertEqual(event1.tick, event2.tick)
                self.assertEqual(event1.data, event2.data)


if __name__ == '__main__':
    unittest.main()
