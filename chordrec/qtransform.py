import librosa
from argparse import ArgumentParser

def compute_cqts(data_dir, audio_dir, n_processes):
    pass

def main():
    parser = ArgumentParser()
    parser.add_argument('-d', '--data-dir')
    parser.add_argument('-a', '--audio-dir')
    parser.add_argument('-p', '--processes')
    args = parser.parse_args()
    compute_cqts(args.data_dir, args.audio_dir, args.processes)

if __name__ == '__main__':
    main()
