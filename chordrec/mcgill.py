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


def chord_per_beat(chords_filename, echonest_filename):
    beats = []
    with open(echonest_filename) as f:
        analysis = json.load(f)
        segments = analysis['segments']
        for segment in segments:
            start = segment['start']
            end = segment['duration'] + start
            beats.append(Beat(start=start, end=end))

    chords = []
    with open(chords_filename) as f:
        for line in f:
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
