#!/bin/bash
set -e # everything must succeed.
echo "[-] install.sh"

. mkvenv.sh

source venv/bin/activate

if [ -e requirements.lock ]; then
    # just delete the .lock file when you want to recreate it
    pip install -r requirements.lock
else
    pip install -r requirements.txt
    echo "locking..."
    pip freeze > requirements.lock
    echo "wrote 'requirements.lock'"
fi

if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi

echo "[✓] install.sh"
