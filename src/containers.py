from __future__ import division

from pprint import pformat

import bisect
import events
import util


class Pattern(list):
    def __init__(self, tracks=[], resolution=220, format=1, tick_relative=True):
        self.format = format
        self.resolution = resolution
        self.tick_relative = tick_relative
        super(Pattern, self).__init__(tracks)

    def get_tick_converter(self):
        """
        creates a TickConverter instance from this guy. Only valid while tempo state of this pattern does not change
        :return: TickConverter
        """
        tempos = []
        for track in self:
            tempos.extend(filter(lambda e: isinstance(e, events.SetTempoEvent), track))
        return TickConverter(tempos, self.resolution)

    def make_ticks_abs(self):
        self.tick_relative = False
        for track in self:
            track.make_ticks_abs()

    def make_ticks_rel(self):
        self.tick_relative = True
        for track in self:
            track.make_ticks_rel()

    def __repr__(self):
        return "midi.Pattern(format=%r, resolution=%r, tracks=\\\n%s)" % \
               (self.format, self.resolution, pformat(list(self)))

    def __getitem__(self, item):
        if isinstance(item, slice):
            indices = item.indices(len(self))
            return Pattern(resolution=self.resolution, format=self.format,
                           tracks=[super(Pattern, self).__getitem__(i) for i in xrange(*indices)])
        else:
            return super(Pattern, self).__getitem__(item)

    def __getslice__(self, i, j):
        # The deprecated __getslice__ is still called when subclassing built-in types
        # for calls of the form List[i:j]
        return self.__getitem__(slice(i, j))


class Track(list):
    def __init__(self, events=[], tick_relative=True):
        self.tick_relative = tick_relative
        super(Track, self).__init__(events)

    def get_text(self, metacommand, dfault=None):
        result=getattr(util.find(lambda e: isinstance(e, events.MetaEventWithText) and e.metacommand==metacommand, self), "text", None)
        if result is not None:
            return result
        return dfault() if callable(dfault) else dfault

    def make_ticks_abs(self):
        if (self.tick_relative):
            self.tick_relative = False
            running_tick = 0
            for event in self:
                event.tick += running_tick
                running_tick = event.tick

    def make_ticks_rel(self):
        if (not self.tick_relative):
            self.tick_relative = True
            running_tick = 0
            for event in self:
                event.tick -= running_tick
                running_tick += event.tick

    def __getitem__(self, item):
        if isinstance(item, slice):
            indices = item.indices(len(self))
            return Track([super(Track, self).__getitem__(i) for i in xrange(*indices)])
        else:
            return super(Track, self).__getitem__(item)

    def __getslice__(self, i, j):
        # The deprecated __getslice__ is still called when subclassing built-in types
        # for calls of the form List[i:j]
        return self.__getitem__(slice(i, j))

    def __repr__(self):
        return "midi.Track(\\\n  %s)" % (pformat(list(self)).replace('\n', '\n  '),)


class TickConverter():
    def __init__(self, tempos, resolution=220):
        """
        constructor
        :param tempos: collection of SetTempoEvent
        :param resolution:
        """
        self._tempos=list(tempos)
        self._resolution=resolution
        self._tempos.sort(cmp=lambda a, b: a.offset-b.offset)
        self._offsets=tuple(map(lambda e: e.offset, self._tempos))
        self._seconds=[0.0]
        for index in range(1, len(self._tempos)):
            tempo_p=self._tempos[index-1]
            tempo_c=self._tempos[index]
            self._seconds.append(self._seconds[index-1]+self._ticks_at_tempo_to_seconds(tempo_c.offset-tempo_p.offset, tempo_p))

    def offset_to_seconds(self, offset):
        index=bisect.bisect_right(self._offsets, offset)-1
        return self._seconds[index]+self._ticks_at_tempo_to_seconds(offset-self._offsets[index], self._tempos[index])

    def event_to_seconds(self, event):
        return self.offset_to_seconds(event.offset)

    def _ticks_at_tempo_to_seconds(self, ticks, tempo):
        return (ticks/float(self._resolution))*tempo.spqn
