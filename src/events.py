import copy
import math

class EventRegistry(object):
    Events = {}
    MetaEvents = {}

    def register_event(cls, event, bases):
        if (Event in bases) or (NoteEvent in bases):
            assert event.statusmsg not in cls.Events, "Event %s already registered" % event.name
            cls.Events[event.statusmsg] = event
        elif (MetaEvent in bases) or (MetaEventWithText in bases):
            if event.metacommand is not None:
                assert event.metacommand not in cls.MetaEvents, "Event %s already registered" % event.name
                cls.MetaEvents[event.metacommand] = event
        else:
            raise ValueError, "Unknown bases class in event type: "+event.name
    register_event = classmethod(register_event)


class AbstractEvent(object):
    name = "Generic MIDI Event"
    length = 0
    statusmsg = 0x0
    __slots__ = ['offset', 'data']

    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            if name not in ['AbstractEvent', 'Event', 'MetaEvent', 'NoteEvent', 'MetaEventWithText']:
                EventRegistry.register_event(cls, bases)

    def __init__(self, **kw):
        self.offset = 0
        if type(self.length) == int:
            self.data = [0] * self.length
        else:
            self.data = []
        for key in kw:
            setattr(self, key, kw[key])

    def __deepcopy__(self, memo, keys=tuple()):
        kargs={}
        for key in keys+('offset', 'data'):
            kargs[key]=copy.deepcopy(getattr(self, key), memo)
        return EventRegistry.Events[self.statusmsg](**kargs)

    def __baserepr__(self, keys=tuple()):
        keys = ('offset',) + keys + ('data',)
        body = []
        for key in keys:
            val = getattr(self, key)
            keyval = "%s=%r" % (key, val)
            body.append(keyval)
        body = str.join(', ', body)
        return "midi.%s(%s)" % (self.__class__.__name__, body)

    def __repr__(self):
        return self.__baserepr__()


class Event(AbstractEvent):
    name = 'Event'
    __slots__ = ['channel']

    def __init__(self, **kw):
        if 'channel' not in kw:
            kw = kw.copy()
            kw['channel'] = 0
        super(Event, self).__init__(**kw)

    def __deepcopy__(self, memo, keys=tuple()):
        return super(Event, self).__deepcopy__(memo, keys + ('channel',))

    def __repr__(self):
        return self.__baserepr__(('channel',))

    def is_event(cls, statusmsg):
        return (cls.statusmsg == (statusmsg & 0xF0))
    is_event = classmethod(is_event)


"""
MetaEvent is a special subclass of Event that is not meant to
be used as a concrete class.  It defines a subset of Events known
as the Meta events.
"""
class MetaEvent(AbstractEvent):
    statusmsg = 0xFF
    metacommand = 0x0
    name = 'Meta Event'

    def is_event(cls, statusmsg):
        return (statusmsg == 0xFF)
    is_event = classmethod(is_event)


"""
NoteEvent is a special subclass of Event that is not meant to
be used as a concrete class.  It defines the generalities of NoteOn
and NoteOff events.
"""
class NoteEvent(Event):
    length = 2
    __slots__ = ['pitch', 'velocity']

    def get_pitch(self):
        return self.data[0]
    def set_pitch(self, val):
        self.data[0] = val
    pitch = property(get_pitch, set_pitch)

    def get_velocity(self):
        return self.data[1]
    def set_velocity(self, val):
        self.data[1] = val
    velocity = property(get_velocity, set_velocity)

    def __repr__(self):
        return self.__baserepr__(('channel', 'pitch', 'velocity'))


class NoteOnEvent(NoteEvent):
    statusmsg = 0x90
    name = 'Note On'
    __slots__ = ['duration']

    def __init__(self, **kw):
        self.duration=0     # default in event that it is not known yet
        super(NoteOnEvent, self).__init__(**kw)

    def __deepcopy__(self, memo, keys=tuple()):
        return super(NoteOnEvent, self).__deepcopy__(memo, keys + ('duration',))

    def __repr__(self):
        return self.__baserepr__(('channel', 'pitch', 'velocity', 'duration'))


class NoteOffEvent(NoteEvent):
    statusmsg = 0x80
    name = 'Note Off'


class AfterTouchEvent(Event):
    statusmsg = 0xA0
    length = 2
    name = 'After Touch'

    def get_pitch(self):
        return self.data[0]
    def set_pitch(self, val):
        self.data[0] = val
    pitch = property(get_pitch, set_pitch)

    def get_value(self):
        return self.data[1]
    def set_value(self, val):
        self.data[1] = val
    value = property(get_value, set_value)


class ControlChangeEvent(Event):
    statusmsg = 0xB0
    length = 2
    name = 'Control Change'
    __slots__ = ['control', 'value']

    def set_control(self, val):
        self.data[0] = val
    def get_control(self):
        return self.data[0]
    control = property(get_control, set_control)

    def set_value(self, val):
        self.data[1] = val
    def get_value(self):
        return self.data[1]
    value = property(get_value, set_value)


class ProgramChangeEvent(Event):
    statusmsg = 0xC0
    length = 1
    name = 'Program Change'
    __slots__ = ['value']

    def set_value(self, val):
        self.data[0] = val
    def get_value(self):
        return self.data[0]
    value = property(get_value, set_value)


class ChannelAfterTouchEvent(Event):
    statusmsg = 0xD0
    length = 1
    name = 'Channel After Touch'
    __slots__ = ['value']

    def set_value(self, val):
        self.data[1] = val
    def get_value(self):
        return self.data[1]
    value = property(get_value, set_value)


class PitchWheelEvent(Event):
    statusmsg = 0xE0
    length = 2
    name = 'Pitch Wheel'
    __slots__ = ['pitch']

    def get_pitch(self):
        return ((self.data[1] << 7) | self.data[0]) - 0x2000
    def set_pitch(self, pitch):
        value = pitch + 0x2000
        self.data[0] = value & 0x7F
        self.data[1] = (value >> 7) & 0x7F
    pitch = property(get_pitch, set_pitch)


class SysexEvent(Event):
    statusmsg = 0xF0
    name = 'SysEx'
    length = 'varlen'

    def is_event(cls, statusmsg):
        return (cls.statusmsg == statusmsg)
    is_event = classmethod(is_event)


class SequenceNumberMetaEvent(MetaEvent):
    name = 'Sequence Number'
    metacommand = 0x00
    length = 2


class MetaEventWithText(MetaEvent):
    length = 'varlen'

    def __init__(self, **kw):
        super(MetaEventWithText, self).__init__(**kw)
        if 'text' not in kw:
            self.text = ''.join(chr(datum) for datum in self.data)
        elif 'data' not in kw:
            self.data = [ord(c) for c in kw["text"]]

    def __repr__(self):
        return self.__baserepr__(('text',))


class TextMetaEvent(MetaEventWithText):
    name = 'Text'
    metacommand = 0x01

class CopyrightMetaEvent(MetaEventWithText):
    name = 'Copyright Notice'
    metacommand = 0x02

class TrackNameEvent(MetaEventWithText):
    name = 'Track Name'
    metacommand = 0x03

class InstrumentNameEvent(MetaEventWithText):
    name = 'Instrument Name'
    metacommand = 0x04

class LyricsEvent(MetaEventWithText):
    name = 'Lyrics'
    metacommand = 0x05

class MarkerEvent(MetaEventWithText):
    name = 'Marker'
    metacommand = 0x06

class CuePointEvent(MetaEventWithText):
    name = 'Cue Point'
    metacommand = 0x07

class ProgramNameEvent(MetaEventWithText):
    name = 'Program Name'
    metacommand = 0x08

class UnknownMetaEvent(MetaEvent):
    name = 'Unknown'
    # This class variable must be overriden by code calling the constructor,
    # which sets a local variable of the same name to shadow the class variable.
    metacommand = None

    def __init__(self, **kw):
        super(MetaEvent, self).__init__(**kw)
        self.metacommand = kw['metacommand']


class ChannelPrefixEvent(MetaEvent):
    name = 'Channel Prefix'
    metacommand = 0x20
    length = 1

class PortEvent(MetaEvent):
    name = 'MIDI Port/Cable'
    metacommand = 0x21

class TrackLoopEvent(MetaEvent):
    name = 'Track Loop'
    metacommand = 0x2E

class EndOfTrackEvent(MetaEvent):
    name = 'End of Track'
    metacommand = 0x2F

class SetTempoEvent(MetaEvent):
    name = 'Set Tempo'
    metacommand = 0x51
    length = 3
    __slots__ = ['bpm', 'mpqn']

    def __deepcopy__(self, memo, keys=tuple()):
        return super(SetTempoEvent, self).__deepcopy__(memo, keys + ('bpm', 'mpqn'))

    def get_bpm(self):
        """
        beats/minute
        :return: float
        """
        return 60000000.0 / self.mpqn
    def set_bpm(self, bpm):
        self.mpqn = int(60000000.0 / bpm)
    bpm = property(get_bpm, set_bpm)

    def get_mpqn(self):
        """
        microseconds/beat
        :return: int
        """
        assert(len(self.data) == 3)
        return sum((self.data[x] << (16 - (8 * x)) for x in xrange(3)))
    def set_mpqn(self, val):
        self.data = [(val >> (16 - (8 * x)) & 0xFF) for x in range(3)]
    mpqn = property(get_mpqn, set_mpqn)

    def get_spqn(self):
        """
        seconds/beat
        :return: float
        """
        return self.mpqn/float(1000000)
    spqn = property(get_spqn)

    def __repr__(self):
        return self.__baserepr__(('bpm',))


class SmpteOffsetEvent(MetaEvent):
    name = 'SMPTE Offset'
    metacommand = 0x54

class TimeSignatureEvent(MetaEvent):
    name = 'Time Signature'
    metacommand = 0x58
    length = 4
    __slots__ = ['numerator', 'denominator', 'metronome', 'thirtyseconds']

    def get_numerator(self):
        return self.data[0]
    def set_numerator(self, val):
        self.data[0] = val
    numerator = property(get_numerator, set_numerator)

    def get_denominator(self):
        return 2 ** self.data[1]
    def set_denominator(self, val):
        self.data[1] = int(math.log(val, 2))
    denominator = property(get_denominator, set_denominator)

    def get_metronome(self):
        return self.data[2]
    def set_metronome(self, val):
        self.data[2] = val
    metronome = property(get_metronome, set_metronome)

    def get_thirtyseconds(self):
        return self.data[3]
    def set_thirtyseconds(self, val):
        self.data[3] = val
    thirtyseconds = property(get_thirtyseconds, set_thirtyseconds)


class KeySignatureEvent(MetaEvent):
    name = 'Key Signature'
    metacommand = 0x59
    length = 2
    __slots__ = ['alternatives', 'minor']

    def get_alternatives(self):
        d = self.data[0]
        return d - 256 if d > 127 else d
    def set_alternatives(self, val):
        self.data[0] = 256 + val if val < 0 else val
    alternatives = property(get_alternatives, set_alternatives)

    def get_minor(self):
        return self.data[1]
    def set_minor(self, val):
        self.data[1] = val
    minor = property(get_minor, set_minor)


class SequencerSpecificEvent(MetaEvent):
    name = 'Sequencer Specific'
    metacommand = 0x7F
