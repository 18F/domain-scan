#!/bin/bash

aws lambda invoke \
  --function-name pshtt_test \
  --payload "{\"url\": \"$1\"}" \
  --invocation-type Event \
  output-test.txt
