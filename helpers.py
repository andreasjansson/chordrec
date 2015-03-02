AWS_ACCESS_KEY_ID = 'fill me out'
AWS_SECRET_ACCESS_KEY = 'fill me out'
S3_BUCKET = 'fill me out'

import numpy as np
import cPickle
import json
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import sys
from collections import namedtuple

import theano
import theano.tensor as T
floatX = theano.config.floatX

import matplotlib.pyplot as plt
plt.rcParams['figure.figsize'] = (10.0, 8.0)
plt.rcParams['figure.facecolor'] = 'white'
imshow = lambda x, *args, **kwargs: plt.imshow(x, interpolation='none', aspect='auto', cmap='hot', *args, **kwargs)

def s3_get(path, unpickle=False):
    conn = S3Connection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    bucket = conn.get_bucket(S3_BUCKET)
    key = Key(bucket)
    key.key = path
    data = key.get_contents_as_string()
    if unpickle:
        data = cPickle.loads(data)
    return data

def s3_put(path, data, pickle=False):
    conn = S3Connection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    bucket = conn.get_bucket(S3_BUCKET)
    key = Key(bucket)
    key.key = path
    if pickle:
        data = cPickle.dumps(data, protocol=cPickle.HIGHEST_PROTOCOL)
    key.set_contents_from_string(data)

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

    @staticmethod
    def from_number(x):
        if x == 24:
            return Chord(None, NO_CHORD)
        if x == 25:
            return Chord(None, None)
        root = int(x / 2)
        quality = ['maj', 'min'][root % 2]
        return Chord(root, quality)

    def __repr__(self):
        if self.root is None:
            s = self.quality
        else:
            s = self.to_string()
        return '<Chord: %s>' % s

    def to_string(self):
        return '%s:%s' % (NOTE_NAMES[self.root], self.quality)

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
    beats_json = analysis['beats']
    for beat_json in beats_json:
        start = beat_json['start']
        end = beat_json['duration'] + start
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
        root = get_note_number(root)
        chord = Chord(root, quality)
    return chord


Note = namedtuple('Note', ['name', 'fq', 'midi_pitch'])

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

ENHARMONIC_EQUIVALENTS = {
    'C#': 'Db',
    'Db': 'C#',
    'D#': 'Eb',
    'Eb': 'D#',
    'E' : 'Fb',
    'Fb': 'E',
    'E#': 'F',
    'F' : 'E#',
    'F#': 'Gb',
    'Gb': 'F#',
    'G#': 'Ab',
    'Ab': 'G#',
    'A#': 'Bb',
    'Bb': 'A#',
    'B' : 'Cb',
    'Cb': 'B',
    'B#': 'C',
    'C' : 'B#',
}

MIDI_FREQS = {}

def _setup_notes():
    for octave in range(0, 7):
        for i, note_name in enumerate(NOTE_NAMES):
            dist_from_a = (octave - 3) * 12 + i - 9
            fq = 440 * np.power(2, dist_from_a / 12.0)
            midi_pitch = (octave + 1) * 12 + i

            MIDI_FREQS[midi_pitch] = fq

            note_names = [note_name]
            if note_name in ENHARMONIC_EQUIVALENTS:
                note_names.append(ENHARMONIC_EQUIVALENTS[note_name])

            for n in [note_name] + ([ENHARMONIC_EQUIVALENTS[note_name]]
                                    if note_name in ENHARMONIC_EQUIVALENTS else []):
                name = '%s%d' % (n, octave)
                note = Note(name, fq, midi_pitch)
                setattr(sys.modules[__name__], name.replace('#', '_'), note)

_setup_notes()


class UnknownNote(Exception): pass

def get_note_number(note_name):
    if note_name in NOTE_NAMES:
        return NOTE_NAMES.index(note_name)
    elif note_name in ENHARMONIC_EQUIVALENTS:
        return NOTE_NAMES.index(ENHARMONIC_EQUIVALENTS[note_name])
    raise UnknownNote(note_name)

def get_note_name(note_number):
    if note_number < 0:
        raise UnknownNote(note_number)
    name = NOTE_NAMES[note_number % 12]
    octave = int(note_number / 12)
    return '%s%d' % (name, octave)

def pitch_to_freq(pitch):
    return MIDI_FREQS[pitch]


def axes_plot_with_notes(ax, pg, min_pitch, max_pitch):
    ax.imshow(pg[:, min_pitch:max_pitch], interpolation='none', aspect='auto', cmap='hot')
    labels = [NOTE_NAMES[i % 12] for i in range(min_pitch, max_pitch)]
    ax.set_xticks(np.arange(max_pitch - min_pitch))
    ax.set_xticklabels(labels, rotation=90, ha='center')

def plot_with_notes(pg, min_pitch, max_pitch):
    _, ax = plt.subplots(1, 1)
    axes_plot_with_notes(ax, pg, min_pitch, max_pitch)

def plot_with_notes_and_chords(pitchgram, chords, min_time, max_time, min_pitch, max_pitch):
    _, ax = plt.subplots(1, 1)
    axes_plot_with_notes(ax, pitchgram[min_time:max_time], min_pitch, max_pitch)
    axes_add_chord_ticks(ax, chords[min_time:max_time])

def axes_add_chord_ticks(ax, chords):
    ax.yaxis.tick_right()
    ticks = []
    labels = []
    prev = None
    for i, c in enumerate(chords):
        if c != prev:
            ticks.append(i)
            chord = Chord.from_number(c)
            labels.append(chord.to_string())
            prev = c
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels)

