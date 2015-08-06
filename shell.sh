#!/bin/bash
set -e
source install.sh 2&> /dev/null

CONFIG=$1
if [ -f "$CONFIG" ]; then
    set -a; source $CONFIG; set +a;
else
    if [ -f "test-config" ]; then
        set -a; source "test-config"; set +a;
    else
        echo "no config file given for testing. I'll be using the system defaults! beware!"
    fi
fi
ipython2
