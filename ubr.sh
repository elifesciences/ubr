#!/bin/bash
# calls the command line interface to the universal backup/restore script
# assumes script is being run from directory it lives in
set -e
source install.sh

# this script expects config to live in /etc/ubr/
mkdir -p /etc/ubr/
if [ -f /etc/ubr/config ]; then
    set -a; source /etc/ubr/config; set +a;
else
    echo "* couldn't find /etc/ubr/config.yaml - you had better hope all the defaults work"
fi

# call ubr
python ubr/main.py /etc/ubr/
