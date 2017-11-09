#!/bin/bash

FUNCTION_NAME=$1

# From the lambda dir - use the build/ dir to assemble a zip
# and "publish" it back up to the lambda dir.
rm -r build
mkdir -p build
cd build

# Copy the actual used .py files into the build.
cp ../$FUNCTION_NAME.py .

echo "Building zip package..."
zip -rq9 ../$FUNCTION_NAME.zip .
cd ..

# Update the function's code with the latest zipped code.
echo "Publishing to Lambda..."
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://./$FUNCTION_NAME.zip
