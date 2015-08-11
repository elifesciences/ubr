#!/bin/bash
set -e
cd "$(dirname "$0")"
source install.sh 2&> /dev/null

CONFIG=$1
if [ ! -f "$CONFIG" ]; then
    if [ -f /etc/ubr/config ]; then CONFIG="/etc/ubr/config"
    elif [ -f "test-config" ]; then CONFIG="test-config"
    fi
fi

if [ ! -z "$CONFIG" ]; then
    echo "using config $CONFIG"
    set -a; source $CONFIG; set +a;
else
    echo "no config file available for testing. looked for an argument, looked in /etc/ubr/config, looked for test-config and found *nothing*. I'll be using the system defaults! beware!"
fi

`which pylint2 pylint` -E *.py ubr/*.py ubr/tests/*.py; echo 'passed pylint'
#python2 -m unittest discover -s ubr/tests/ -p s3_upload_tests.py 
python2 -m unittest discover -s ubr/tests/ -p *_tests.py

