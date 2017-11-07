#!/bin/bash

FUNCTION_NAME=$1

# The only thing that has changed is some task Python code,
# so do minimal steps to rebuild the zip and publish it.
# (No remote package downloading.)

cd build
# Copy the actual used .py files into the build.
cp ../$FUNCTION_NAME.py .

# Should update zip file in-place.
echo "Rebuilding zip package..."
zip -rq9 ../$FUNCTION_NAME.zip .
cd ..

# Update the function's code with the latest zipped code.
echo "Publishing to Lambda..."
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://./$FUNCTION_NAME.zip
