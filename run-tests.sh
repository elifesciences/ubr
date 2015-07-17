#!/bin/bash
set -e
if [ ! -d venv ]; then
    virtualenv venv --python=`which python2`
fi
source venv/bin/activate
pip install -r requirements.txt

python2 -m unittest discover -s tests/ -p *_tests.py
