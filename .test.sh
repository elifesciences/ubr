#!/bin/bash
# assumes activated venv
set -e

pyflakes ubr/

args="$@"
module=""
if [ ! -z "$args" ]; then
    # like this for pytest:
    # ./ubr/tests/test_main.py::ParseArgs::test_download_adhoc_args
    module="$args"
fi

if [ ! -e test-config ]; then
    cp example.config test-config
fi
set -a; source test-config; set +a;

rm -rf build/junit.xml
pytest "$module" -vvv --cov=ubr --junitxml=build/junit.xml
