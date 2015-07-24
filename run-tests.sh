#!/bin/bash
set -e
source install.sh 2&> /dev/null

CONFIG=$1
if [ -f "$CONFIG" ]; then
    echo "given config file $CONFIG"
    set -a; source $CONFIG; set +a;
    echo $MYSQL_USER
else
    if [ -f "test-config" ]; then
        set -a; source "test-config"; set +a;
    else
        echo "no config file given for testing. I'll be using the system defaults! beware!"
    fi
fi
pylint2 -E *.py ubr/tests/*.py
echo 'passed pylint'
python2 -m unittest discover -s ubr/tests/ -p *_tests.py
