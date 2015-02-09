#!/bin/bash

set -eu

python="python2.7"
pip="pip-2.7"

pushd ~/chordrec
sudo $python setup.py install
popd
