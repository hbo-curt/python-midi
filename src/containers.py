from __future__ import division

from pprint import pformat

import bisect

import math

import events
import util

class Pattern(list):
    # noinspection PyDefaultArgument
    def __init__(self, resolution=220, format=1, tracks=[]):
        self.format = format
        self.resolution = resolution
        super(Pattern, self).__init__(tracks)

    #--- public api ---#
    def get_duration(self):
        return max([track.duration for track in self])
    duration=property(get_duration)

    def get_tick_converter(self):
        """
        creates a TickConverter instance from this guy. Only valid while tempo state of this pattern does not change
        :return: TickConverter
        """
        tempos = []
        for track in self:
            tempos.extend(filter(lambda e: isinstance(e, events.SetTempoEvent), track))
        return TickConverter(tempos, self.resolution)

    def nearest_quantized_duration(self, duration):
        if duration<=1:
            return 1
        power=int(math.floor(math.log(duration/self.resolution, 2)))
        # division: 1=whole, 3/4=dotted, 2/3=triplet
        ratios=((pow(2, ratio) * multiple) for ratio in range(power, power+2) for multiple in (2/3, 3/4, 1))
        quantized=[int(self.resolution*ratio) for ratio in ratios if int(self.resolution*ratio)>0]
        for index in range(1, len(quantized)):
            if duration<=quantized[index]:
                return quantized[index] if quantized[index]-duration<duration-quantized[index-1] else quantized[index-1]
        return quantized[-1]

    #--- private api ---#
    def __repr__(self):
        return "midi.Pattern(format=%r, resolution=%r, tracks=\\\n%s)" % \
               (self.format, self.resolution, pformat(list(self)))

    def __getitem__(self, item):
        if isinstance(item, slice):
            indices=item.indices(len(self))
            return Pattern(resolution=self.resolution, format=self.format, tracks=[super(Pattern, self).__getitem__(i) for i in xrange(*indices)])
        else:
            return super(Pattern, self).__getitem__(item)

    def __getslice__(self, i, j):
        # The deprecated __getslice__ is still called when subclassing built-in types
        # for calls of the form List[i:j]
        return self.__getitem__(slice(i, j))


class Track(list):
    # noinspection PyDefaultArgument
    def __init__(self, events=[]):
        super(Track, self).__init__(events)

    #--- public api ---#
    def get_duration(self):
        return max([event.offset+getattr(event, "duration", 0) for event in self])
    duration=property(get_duration)

    def insert_event(self, event, bias="right"):
        vof = util.bisect_left if bias=="left" else util.bisect_right
        index = vof(a=self, x=event.offset, vof=lambda o: o.offset)
        self.insert(index, event)

    def get_text(self, metacommand, dfault=None):
        result=getattr(util.find(lambda e: isinstance(e, events.MetaEventWithText) and e.metacommand==metacommand, self), "text", None)
        if result is not None:
            return result
        return dfault() if callable(dfault) else dfault

    #--- private api ---#
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

    def duration_to_seconds(self, offset, duration):
        return self.offset_to_seconds(offset+duration)-self.offset_to_seconds(offset)

    def event_to_seconds(self, event):
        """
        get offset and duration
        :param event: midi.Event
        :return: (offset, duration)
        """
        offset=self.offset_to_seconds(event.offset)
        return offset, (self.offset_to_seconds(event.offset+event.duration)-offset)

    #--- private api ---#
    def _ticks_at_tempo_to_seconds(self, ticks, tempo):
        return (ticks/float(self._resolution))*tempo.spqn
