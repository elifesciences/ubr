#!/bin/bash
set -e
source install.sh
pylint2 -E *.py ubr/tests/*.py
echo 'passed pylint'
python2 -m unittest discover -s ubr/tests/ -p *_tests.py
