#!/bin/bash
set -e
cd "$(dirname "$0")"
source install.sh
source .lint.sh
source .scrub.sh
source .unittest.sh
