#!/bin/bash

cd $(dirname "$0")

# Run tests, coverage, and flake8

RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
RESET=$(tput sgr0)
EXIT_CODE=0

_flake8() {
  flake8 s3_browser setup.py
  if [[ "$?" != 0 ]]; then
    EXIT_CODE="$?"
  else
    echo "${GREEN}Flake8 check passed!$RESET"
  fi
}

mkdir -p build

echo -n "$RED"
_flake8 | tee build/flake8.log
echo -n "$RESET"


echo ''

nosetests \
  --with-coverage \
  --cover-package s3_browser \
  --cover-inclusive \
  --cover-html \
  --cover-min-percentage 85 \
  --cover-html-dir build/coverage || exit 1

exit $EXIT_CODE
