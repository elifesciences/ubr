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
green ubr/ --run-coverage --processes 1 -vv
