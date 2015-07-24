#!/bin/bash
# calls the command line interface to the universal backup/restore script
set -e
source install.sh
if [ -f /etc/ubr/config ]; then
    source /etc/ubr/config
else
    echo "* couldn't find /etc/ubr/config - you had better hope all the defaults work"
fi
python ubr/main.py /etc/ubr/
