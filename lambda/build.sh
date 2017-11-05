#!/bin/bash

# From the lambda dir - use the build/ dir to assemble a zip
# and "publish" it back up to the lambda dir.
mkdir -p build
echo "Building zip package..."
cd build
cp ../pshtt_test.py .
cp -r $HOME/.virtualenvs/lambda/lib/python3.6/site-packages/* .
zip -rq9 ../pshtt_test.zip .
cd ..

# Update the function's code with the latest zipped code.
echo "Publishing to Lambda..."
aws lambda update-function-code \
  --function-name pshtt_test \
  --zip-file fileb://./pshtt_test.zip
