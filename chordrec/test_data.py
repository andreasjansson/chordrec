import numpy as np
from andreasmusic import audio, pitches, spectrum
from glob import glob
import random
from chordrec import mcgill
import json

AUDIO_DIR = '/home/andreas/phd/data/billboard/audio'
MCGILL_DIR = '/home/andreas/phd/data/billboard/McGill-Billboard'

def get_test_data(count=1):
    test_data = []
    data_folders = glob('%s/*' % MCGILL_DIR)
    while len(test_data) < count:
        data_folder = random.choice(data_folders)
        echonest_filename = '%s/echonest.json' % data_folder
        chords_filename = '%s/majmin.lab' % data_folder
        with open(echonest_filename) as f:
            echonest_json = json.load(f)

        audio_filename = echonest_json['meta']['filename'].split('/')[-1]
        audio_path = '%s/%s' % (AUDIO_DIR, audio_filename)
        beats = mcgill.chord_per_beat(chords_filename, echonest_filename)
        pitchgram = get_beat_aligned_pitchgram(audio_path, beats)
        classes = np.array([get_chord_number(b.chord) for b in beats])
        test_data.append((pitchgram, classes))

    return test_data

def get_chord_number(chord):
    if chord.root is None:
        if chord.quality == mcgill.NO_CHORD:
            return 24
        else:
            return 25
    n = chord.root * 2

    if chord.quality == 'maj':
        return n
    elif chord.quality == 'min':
        return n + 1

    raise Exception('Unknown chord: %s' % chord)

def get_beat_aligned_pitchgram(audio_path, beats, min_pitch=3*12, max_pitch=7*12, window_size=4096, hop_size=2048):
    a = audio.read(audio_path).get_channel(0).downsample(4)
    pitchgram = audio_to_pitchgram(a, min_pitch, max_pitch, window_size, hop_size)
    step = float(hop_size) / a.sample_rate
    timed_pitchgram = [(i * step, (i + 1) * step, p) for i, p in enumerate(pitchgram)]
    aligned_pitchgram = mcgill.beat_align(beats, timed_pitchgram)

    return np.array(aligned_pitchgram)

def audio_to_pitchgram(a, min_pitch, max_pitch, window_size, hop_size):
    spectrogram = spectrum.get_spectrogram(a, window_size=window_size, hop_size=hop_size)

    bins = 12
    min_fq = pitches.pitch_to_freq(min_pitch)

    indices = np.round(bins * np.log2(
        (a.sample_rate / 2.0) *
        np.arange(1, window_size / 2) /
        (window_size / 2) / min_fq)
    ).astype(int)

    n_pitches = (max_pitch - min_pitch)
    good_indices = np.where((indices >= 0) & (indices < n_pitches))

    pitchgram = np.zeros((spectrogram.shape[0], n_pitches))
    for i, s in enumerate(spectrogram):
        pitchgram[i] = np.bincount(indices[good_indices], weights=s[good_indices])

    pitchgram /= np.bincount(indices[good_indices])
    pitchgram /= np.max(pitchgram)

    return pitchgram
