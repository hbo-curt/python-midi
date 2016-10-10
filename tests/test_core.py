from __future__ import division
import unittest
import midi


class TestUtil(unittest.TestCase):
    def test_varlen(self):
        maxval = 0x0FFFFFFF
        for inval in xrange(0, maxval, int(maxval / 1000)):
            datum = midi.write_varlen(inval)
            outval = midi.read_varlen(iter(datum))
            self.assertEqual(inval, outval)


class TestEvents(unittest.TestCase):
    def test_note_on(self):
        event=midi.NoteOnEvent(channel=0, offset=1, duration=2, pitch=4, velocity=3)
        self.assertEqual(event.channel, 0)
        self.assertEqual(event.offset, 1)
        self.assertEqual(event.duration, 2)
        self.assertEqual(event.velocity, 3)
        self.assertEqual(event.pitch, 4)
        self.assertEqual(event.data, [4, 3])


class TestContainers(unittest.TestCase):
    def test_track_insert(self):
        track=midi.Track()
        event=midi.AbstractEvent(offset=0); track.insert_event(event)
        self.assertEqual(track[0], event)
        event=midi.AbstractEvent(offset=0); track.insert_event(event, bias="left")
        self.assertEqual(track[0], event)
        event=midi.AbstractEvent(offset=0); track.insert_event(event, bias="right")
        self.assertEqual(track[2], event)
        event=midi.AbstractEvent(offset=1); track.insert_event(event)
        self.assertEqual(track[3], event)

    def test_duration_without_duration(self):
        track=midi.Track()
        track.insert_event(midi.AbstractEvent(offset=0))
        track.insert_event(midi.AbstractEvent(offset=1))
        self.assertEqual(track.duration, 1)

    def test_duration_with_duration(self):
        track=midi.Track()
        track.insert_event(midi.AbstractEvent(offset=10))
        track.insert_event(midi.NoteOnEvent(offset=0, duration=11))
        self.assertEqual(track.duration, 11)


class TestPattern(unittest.TestCase):
    def test_construction(self):
        pattern=midi.Pattern(resolution=10, format=11)
        self.assertEqual(pattern.resolution, 10)
        self.assertEqual(pattern.format, 11)

    def test_duration(self):
        pattern=midi.Pattern()
        track=midi.Track()
        track.insert_event(midi.AbstractEvent(offset=11))
        pattern.append(track)
        track=midi.Track()
        track.insert_event(midi.AbstractEvent(offset=10))
        pattern.append(track)
        self.assertEqual(pattern.duration, 11)

    def test_quantize(self):
        pattern=midi.Pattern(resolution=64)
        values=((64*8+64/8, 64*8), (64*8, 64*8), (64*8-64/8, 64*8),
                (64*2+64/8, 64*2), (64*2, 64*2), (64*2-64/8, 64*2),
                (65, 64), (64, 64), (63, 64),
                (49, 48), (47, 48),
                (33, 32), (15, 16), (4, 4), (3, 3), (1, 1), (0, 1))
        for v in values:
            self.assertEqual(pattern.nearest_quantized_duration(v[0]), v[1])

class TestTickConverter(unittest.TestCase):
    def setUp(self):
        # tempo.mid:
        #   - resolution: 480
        #   - tempos: [{0: 30}, {480: 60}, {960: 90}, {1440, 120}]
        self.pattern=midi.read_midifile("./data/tempo.mid")
        self.converter=self.pattern.get_tick_converter()
        self.assertEqual(self.pattern.resolution, 480)
        self.assertEqual(len(filter(lambda e: isinstance(e, midi.SetTempoEvent), self.pattern[0])), 4)

    def test_offset_to_seconds(self):
        self.assertEqual(self.converter.offset_to_seconds(480*0), 0)
        self.assertEqual(self.converter.offset_to_seconds(480*4), 60/30*4)
        self.assertAlmostEqual(self.converter.offset_to_seconds(480*8), 60/30*4+60/60*4, places=5)
        self.assertAlmostEqual(self.converter.offset_to_seconds(480*12), 60/30*4+60/60*4+60/90*4, places=5)
        self.assertAlmostEqual(self.converter.offset_to_seconds(480*16), 60/30*4+60/60*4+60/90*4+60/120*4, places=5)
        self.assertAlmostEqual(self.converter.offset_to_seconds(480*10), 60/30*4+60/60*4+60/90*2, places=5)

    def test_duration_to_seconds(self):
        self.assertEqual(self.converter.duration_to_seconds(0, 0), 0)
        self.assertEqual(self.converter.duration_to_seconds(0, 480*4), 60/30*4)
        self.assertAlmostEqual(self.converter.duration_to_seconds(480*2, 480*4), 60/30*2+60/60*2, places=5)


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

    def test_write(self):
        pattern1=midi.read_midifile("./data/tempo.mid")
        midi.write_midifile("./data/test.mid", pattern1)
        pattern2=midi.read_midifile("./data/test.mid")
        self.assertEqual(len(pattern1), len(pattern2))
        for track_idx in range(len(pattern1)):
            self.assertEqual(len(pattern1[track_idx]), len(pattern2[track_idx]))
            for event_idx in range(len(pattern1[track_idx])):
                event1=pattern1[track_idx][event_idx]
                event2=pattern2[track_idx][event_idx]
                self.assertEqual(event1.data, event2.data)


if __name__ == '__main__':
    unittest.main()
