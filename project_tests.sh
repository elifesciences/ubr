#!/bin/bash
set -e

# test config (see libraries formula)
# - https://github.com/elifesciences/elife-libraries-formula/blob/1f275e206f2b398ce49ba14e4a277905a5b8d332/salt/elife-libraries/init.sls#L132-L138
rm -f app.cfg
cp /etc/ubr-test-app.cfg app.cfg

source test.sh
