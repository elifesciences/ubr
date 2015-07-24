#!/bin/bash
# creates virtualenv, installs python dependencies
# used by other scripts to ensure a working env exists
set -e
if [ ! -d venv ]; then
    virtualenv venv --python=`which python2`
    pip install -r requirements.txt # show output first time
fi
source venv/bin/activate
pip install -r requirements.txt > /dev/null # suppress output from now on
