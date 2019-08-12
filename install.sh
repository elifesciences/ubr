#!/bin/bash
set -e # everything must succeed.
echo "[-] install.sh"

. mkvenv.sh

source venv/bin/activate

if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi

pip install -r requirements.txt

echo "[✓] install.sh"
