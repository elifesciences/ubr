#!/bin/bash
set -e

. mkvenv.sh

source venv/bin/activate
pip install pip wheel --upgrade
pip install -r requirements.txt --progress-bar off

if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (example.cfg) by default."
    ln -sf example.cfg app.cfg
fi
