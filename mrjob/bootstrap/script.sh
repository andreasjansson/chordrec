#!/bin/bash

set -eu

python="python2.7"
pip="pip"

sudo yum install -y \
    git \
    emacs \
    mlocate \
    htop \

if [ ! -e libsamplerate-0.1.8 ]
then
    wget http://www.mega-nerd.com/SRC/libsamplerate-0.1.8.tar.gz
    tar xzvf libsamplerate-0.1.8.tar.gz
    pushd libsamplerate-0.1.8
    ./configure --prefix=/usr
    make
    sudo make install
    sudo ldconfig
    popd
fi

sudo $pip install -U pip

sudo $pip install \
    ipdb \
    mrjob \
    nose \
    'https://pypi.python.org/packages/source/l/librosa/librosa-0.3.0.tar.gz#md5=1bc1d964b894a04a6b9642304322aeab' \
    scikits.samplerate \

sudo rm -rf andreasmusic
git clone https://github.com/andreasjansson/andreasmusic
pushd andreasmusic
sudo $python setup.py install
popd

wget http://ffmpeg.gusari.org/static/64bit/ffmpeg.static.64bit.2014-03-02.tar.gz
tar xzvf ffmpeg.static.64bit.2014-03-02.tar.gz
sudo cp ffmpeg /usr/bin/ffmpeg

sudo updatedb
