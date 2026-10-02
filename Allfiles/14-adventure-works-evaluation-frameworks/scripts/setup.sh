#!/usr/bin/env sh
set -eu

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
printf '%s\n' 'Activate with: source .venv/bin/activate'