#!/bin/bash
set -e

# new-style config (see libraries formula)
rm app.cfg
cp /etc/ubr-test-app.cfg app.cfg

# legacy config
echo > test-config
echo MYSQL_USER=elife-libraries >> test-config
echo MYSQL_PWD=elife-libraries >> test-config

source run-tests.sh