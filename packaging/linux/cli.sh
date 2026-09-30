#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(realpath "$0")")"
./klarity cli
