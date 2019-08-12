#!/bin/bash
set -e
./install.sh
source venv/bin/activate
source .lint.sh
source .scrub.sh
source .test.sh
