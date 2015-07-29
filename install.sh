#!/bin/bash
# creates virtualenv, installs python dependencies
# used by other scripts to ensure a working env exists
set -e
if [ ! -d venv ]; then
    echo "no virtualenv found, creating"
    virtualenv venv --python=`which python2`
fi
echo "activating"
source venv/bin/activate
pip install -r requirements.txt
