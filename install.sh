#!/bin/bash
# creates virtualenv, installs python dependencies
# used by other scripts to ensure a working env exists
set -e

if [ ! -d venv ]; then
    # build venv if one doesn't exist
    virtualenv --python=`which python2` venv
fi

source venv/bin/activate

# link the default (elife) config if no app.cfg file found
if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi

pip install -r requirements.txt
