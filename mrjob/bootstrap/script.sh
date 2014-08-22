#!/bin/bash

set -eu

python="python2.7"
pip="pip-2.7"

sudo yum install -y \
    git \
    emacs \
    mlocate \

sudo $pip install \
    ipdb \
    mrjob \
#    'https://pypi.python.org/packages/source/l/librosa/librosa-0.3.0.tar.gz#md5=1bc1d964b894a04a6b9642304322aeab' \

sudo rm -rf andreasmusic

if [ ! -e andreasmusic ]
then
    git clone https://github.com/andreasjansson/andreasmusic
    pushd andreasmusic
    sudo $python setup.py install
    popd
fi

sudo updatedb

wget http://ffmpeg.gusari.org/static/64bit/ffmpeg.static.64bit.2014-03-02.tar.gz
tar xzvf ffmpeg.static.64bit.2014-03-02.tar.gz
sudo cp ffmpeg /usr/bin/ffmpeg
