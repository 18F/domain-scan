#!/bin/bash

aws lambda invoke \
  --function-name pshtt_test \
  --payload "{\"domains\": [\"$1\"]}" \
  --invocation-type Event \
  output-test.txt
