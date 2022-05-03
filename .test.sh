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

# just for safety while using moto.
# if you're doing things correctly these shouldn't be neccessary.
export AWS_ACCESS_KEY_ID='testing'
export AWS_SECRET_ACCESS_KEY='testing'
export AWS_SECURITY_TOKEN='testing'
export AWS_SESSION_TOKEN='testing'
export AWS_DEFAULT_REGION='us-east-1'

rm -rf build/junit.xml
pytest "$module" -vvv --cov=ubr --junitxml=build/junit.xml
