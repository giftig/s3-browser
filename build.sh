#!/bin/bash

cd $(dirname "$0")

# Run tests, coverage, and flake8

RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
RESET=$(tput sgr0)

_flake8() {
  local exit_code=0

  flake8 s3_browser setup.py
  exit_code="$?"

  if [[ "$exit_code" == 0 ]]; then
    echo "${GREEN}Flake8 check passed!$RESET"
  fi

  return "$exit_code"
}

mkdir -p build

echo ''

pytest --cov=s3_browser || exit 1

echo -n "$RED"
_flake8 | tee build/flake8.log || exit 2
echo -n "$RESET"
