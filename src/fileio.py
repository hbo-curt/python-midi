import copy
from warnings import *

from containers import *
from events import *
from struct import unpack, pack
from constants import *
from util import *

class FileReader(object):
    def __init__(self):
        self.running_status=None

    def read(self, midifile):
        pattern = self.parse_file_header(midifile)
        for track in pattern:
            self.parse_track(midifile, track)
        return pattern

    def parse_file_header(self, midifile):
        # First four bytes are MIDI header
        magic = midifile.read(4)
        if magic != 'MThd':
            raise TypeError, "Bad header in MIDI file."
        # next four bytes are header size
        # next two bytes specify the format version
        # next two bytes specify the number of tracks
        # next two bytes specify the resolution/PPQ/Parts Per Quarter
        # (in other words, how many ticks per quater note)
        data = unpack(">LHHH", midifile.read(10))
        hdrsz = data[0]
        format = data[1]
        tracks = [Track() for x in range(data[2])]
        resolution = data[3]
        # XXX: the assumption is that any remaining bytes
        # in the header are padding
        if hdrsz > DEFAULT_MIDI_HEADER_SIZE:
            midifile.read(hdrsz - DEFAULT_MIDI_HEADER_SIZE)
        return Pattern(tracks=tracks, resolution=resolution, format=format)

    def parse_track_header(self, midifile):
        # First four bytes are Track header
        magic = midifile.read(4)
        if magic != 'MTrk':
            raise TypeError, "Bad track header in MIDI file: " + magic
        # next four bytes are track size
        trksz = unpack(">L", midifile.read(4))[0]
        return trksz

    def parse_track(self, midifile, track):
        self.running_status = None
        offset = 0
        pool = {}
        trksz = self.parse_track_header(midifile)
        trackdata = iter(midifile.read(trksz))
        while True:
            try:
                event = self.parse_midi_event(trackdata, offset)
                if isinstance(event, NoteOffEvent):
                    try:
                        # regarding overlapped notes - policy is to resolve the oldest instance
                        note_on=pool[event.pitch].pop(0)
                        note_on.duration=event.offset-note_on.offset
                    except:
                        warn("errant note off: {0}".format(event.pitch))
                elif not isinstance(event, EndOfTrackEvent):
                    track.append(event)
                    if isinstance(event, NoteOnEvent):
                        pool.setdefault(event.pitch, []).append(event)
                offset = event.offset
            except StopIteration:
                def _concat(a, k): a.extend(pool[k]); return a
                for event in reduce(_concat, pool, []):
                    warn("unresolved note: {0} at {1}".format(event.pitch, event.offset))
                    track.remove(event)
                break


    def parse_midi_event(self, trackdata, offset):
        # first datum is varlen representing delta-time
        tick = read_varlen(trackdata)
        # next byte is status message
        stsmsg = ord(trackdata.next())
        # is the event a MetaEvent?
        if MetaEvent.is_event(stsmsg):
            cmd = ord(trackdata.next())
            if cmd not in EventRegistry.MetaEvents:
                warn("Unknown Meta MIDI Event: " + `cmd`, Warning)
                cls = UnknownMetaEvent
            else:
                cls = EventRegistry.MetaEvents[cmd]
            datalen = read_varlen(trackdata)
            data = [ord(trackdata.next()) for x in range(datalen)]
            return cls(offset=offset+tick, data=data, metacommand=cmd)
        # is this event a Sysex Event?
        elif SysexEvent.is_event(stsmsg):
            data = []
            while True:
                datum = ord(trackdata.next())
                if datum == 0xF7:
                    break
                data.append(datum)
            return SysexEvent(offset=offset+tick, data=data)
        # not a Meta MIDI event or a Sysex event, must be a general message
        else:
            def _create_event():
                # catch usage of note off to specify a note off
                if key==NoteOnEvent.statusmsg and data[1]==0:
                    return EventRegistry.Events[NoteOffEvent.statusmsg](offset=offset + tick, channel=channel, data=data)
                else:
                    return cls(offset=offset + tick, channel=channel, data=data)

            key = stsmsg & 0xF0
            if key not in EventRegistry.Events:
                assert self.running_status, "Bad byte value"
                key = self.running_status & 0xF0
                cls = EventRegistry.Events[key]
                channel = self.running_status & 0x0F
                data = [stsmsg] + [ord(trackdata.next()) for x in range(cls.length - 1)]
                return _create_event()
            else:
                self.running_status = stsmsg
                cls = EventRegistry.Events[key]
                channel = stsmsg & 0x0F
                data = [ord(trackdata.next()) for x in range(cls.length)]
                return _create_event()


class FileWriter(object):
    def write(self, midifile, pattern):
        self.write_file_header(midifile, pattern)
        for track in pattern:
            self.write_track(midifile, track)

    def write_file_header(self, midifile, pattern):
        # First four bytes are MIDI header
        packdata=pack(">LHHH", 6, pattern.format, len(pattern), pattern.resolution)
        midifile.write('MThd%s'%packdata)

    def write_track(self, midifile, track):
        buf = ''
        offset = 0
        track = copy.copy(track)
        # insert note-off events for all note-on events
        for event in filter(lambda event: isinstance(event, NoteOnEvent), track):
            track.insert_event(NoteOffEvent(channel=event.channel, offset=event.offset+event.duration, data=event.data), bias="left")
        # append end-o-track event
        event=track[-1] if len(track)>0 else None
        track.append(EndOfTrackEvent(offset=getattr(event, "offset", 0)))
        # write events and encode the buffer
        self.RunningStatus = None
        for event in track:
            buf += self.encode_midi_event(event, event.offset-offset)
            offset = event.offset
        buf = self.encode_track_header(len(buf)) + buf
        midifile.write(buf)

    def encode_track_header(self, trklen):
        return 'MTrk%s' % pack(">L", trklen)

    def encode_midi_event(self, event, tick):
        ret = ''
        ret += write_varlen(tick)
        # is the event a MetaEvent?
        if isinstance(event, MetaEvent):
            ret += chr(event.statusmsg) + chr(event.metacommand)
            ret += write_varlen(len(event.data))
            ret += str.join('', map(chr, event.data))
        # is this event a Sysex Event?
        elif isinstance(event, SysexEvent):
            ret += chr(0xF0)
            ret += str.join('', map(chr, event.data))
            ret += chr(0xF7)
        # not a Meta MIDI event or a Sysex event, must be a general message
        elif isinstance(event, Event):
            if not self.RunningStatus or \
                self.RunningStatus.statusmsg != event.statusmsg or \
                self.RunningStatus.channel != event.channel:
                    self.RunningStatus = event
                    ret += chr(event.statusmsg | event.channel)
            ret += str.join('', map(chr, event.data))
        else:
            raise ValueError, "Unknown MIDI Event: " + str(event)
        return ret

def write_midifile(midifile, pattern):
    """
    todo: I broke write when I consolidated note-ons and note-offs.
    need to work note-offs back into the mix
    :param midifile:
    :param pattern:
    :return:
    """
    if type(midifile) in (str, unicode):
        midifile = open(midifile, 'wb')
    writer = FileWriter()
    return writer.write(midifile, pattern)

def read_midifile(midifile):
    if type(midifile) in (str, unicode):
        midifile = open(midifile, 'rb')
    reader = FileReader()
    return reader.read(midifile)
