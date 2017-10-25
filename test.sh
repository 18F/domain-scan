#!/usr/bin/env sh

echo "running linters and tests..."
flake8 . && python -m unittest discover tests
