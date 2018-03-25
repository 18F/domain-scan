#!/usr/bin/env sh

echo "running linters and tests..."
flake8 . && python -m pytest -v tests
