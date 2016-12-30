#!/bin/bash
# calls the command line interface to the universal backup/restore script
# assumes script is being run from directory it lives in
set -e
. install.sh > /dev/null

# this script expects config to live in /etc/ubr/
if [ -f /etc/ubr/config ]; then
    set -a; source /etc/ubr/config; set +a;
else
    echo "* couldn't find /etc/ubr/config - you had better hope all the defaults work"
fi

ipython
