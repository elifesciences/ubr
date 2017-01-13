#!/bin/bash
set -e

echo > test-config
echo MYSQL_USER=elife-libraries >> test-config
echo MYSQL_PWD=elife-libraries >> test-config

source run-tests.sh
