#!/bin/bash
set -e
module=''
if [ ! -z "$@" ]; then
    module=".$@"
fi
if [ ! -e test-config ]; then
    cp example.config test-config
fi
set -a; source test-config; set +a;
nosetests ubr/tests"$module" --config .noserc
coverage report
