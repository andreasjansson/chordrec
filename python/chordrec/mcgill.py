import numpy as np
import simplejson as json
from andreasmusic import pitches

NO_CHORD = 'NO_CHORD'
UNKNOWN = 'UNKNOWN'

class Beat(object):
    def __init__(self, chord=None, start=None, end=None):
        self.chord = chord
        self.start = start
        self.end = end

    def __repr__(self):
        return '<Beat: %s [%.2f, %.2f]>' % (self.chord, self.start, self.end)

    def __str__(self):
        return self.__repr__()

    def to_dict(self):
        return {'chord': self.chord.to_dict(),
                'start': self.start,
                'end': self.end}

class Chord(object):
    def __init__(self, root=None, quality=None):
        self.root = root
        self.quality = quality

    def __repr__(self):
        if self.root is None:
            s = self.quality
        else:
            s = '%s:%s' % (pitches.note_name(self.root), self.quality)
        return '<Chord: %s>' % s

    def to_dict(self):
        return {'root': self.root,
                'quality': self.quality}

    def get_number(self):
        if self.root is None:
            if self.quality == NO_CHORD:
                return 24
            else:
                return 25
        n = self.root * 2

        if self.quality == 'maj':
            return n
        elif self.quality == 'min':
            return n + 1

        raise Exception('Unknown chord: %s' % self)

def chord_per_beat(chords_file, echonest_file):

    if isinstance(chords_file, basestring):
        chords_file = open(chords_file, 'r')
    if isinstance(echonest_file, basestring):
        echonest_file = open(echonest_file, 'r')

    beats = []
    analysis = json.load(echonest_file)
    segments = analysis['segments']
    for segment in segments:
        start = segment['start']
        end = segment['duration'] + start
        beats.append(Beat(start=start, end=end))

    chords = []
    for line in chords_file:
        line = line.strip()
        if not line:
            continue

        start, end, chord = line.split('\t')
        start = float(start)
        end = float(end)
        chord = parse_chord(chord)
        chords.append((start, end, chord))

    chords = beat_align(beats, chords)
    for beat, chord in zip(beats, chords):
        if chord:
            beat.chord = chord
        else:
            beat.chord = parse_chord('N')

    return beats

def beat_align(beats, spans, average=False):
    aligned = []
    i = 0
    if average:
        default = np.zeros(len(spans[0][2]))

    for beat in beats:
        beat_spans = []
        while i < len(spans):
            span_length = min(beat.end, spans[i][1]) - max(beat.start, spans[i][0])
            beat_spans.append((span_length, spans[i][2]))

            if spans[i][1] > beat.end:
                break

            i += 1

        aligned_data = default.copy() if average else None
        max_length = 0
        total_length = beat.end - beat.start
        for length, data in beat_spans:
            if average:
                aligned_data += (data * float(length) / total_length)
            else:
                if length > max_length:
                    max_length = length
                    aligned_data = data

        aligned.append(aligned_data)

    return aligned
        

def parse_chord(chord_name):
    root, _, quality = chord_name.partition(':')
    if root == 'N':
        chord = Chord(None, NO_CHORD)
    elif root == 'X':
        chord = Chord(None, UNKNOWN)
    else:
        root = pitches.note_number(root)
        chord = Chord(root, quality)
    return chord
