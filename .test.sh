#!/bin/bash
# assumes activated venv
set -e

args="$@"
module=""
if [ ! -z "$args" ]; then
    # like this for pytest:
    # ./ubr/tests/test_main.py::ParseArgs::test_download_adhoc_args
    module="$args"
fi

rm -rf build/junit.xml
pytest "$module" -vvv --cov=ubr --junitxml=build/junit.xml
