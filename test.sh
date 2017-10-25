#!/usr/bin/env sh

echo "running linters and tests..."
flake8 --ignore=E722,E501 . && python -m unittest discover tests
