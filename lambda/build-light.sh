#!/bin/bash

SCANNER_NAME=$1
FUNCTION_NAME="task_$SCANNER_NAME"

echo "Building $FUNCTION_NAME from $SCANNER_NAME..."

# From the lambda dir - use the build/ dir to assemble a zip
# and "publish" it back up to the lambda dir.
rm -r build
mkdir -p build
cd build

# Copy the lambda handler, the scanner itself, and utils.
cp ../lambda_handler.py .
mkdir -p scanners
cp ../../scanners/$SCANNER_NAME.py scanners/.
cp ../../scanners/utils.py scanners/.

echo "Building zip package for $FUNCTION_NAME..."
zip -rq9 ../$FUNCTION_NAME.zip .
cd ..

# Update the function's code with the latest zipped code.
# echo "Publishing to Lambda..."
# aws lambda create-function \
#   --function-name $FUNCTION_NAME \
#   --zip-file fileb://./$FUNCTION_NAME.zip \
#   --role $AWS_LAMBDA_ROLE \
#   --handler lambda_handler.handler \
#   --runtime python3.6 \
#   --timeout 30 \
#   --memory-size 128

echo "Updating Lambda handler function for $FUNCTION_NAME..."
aws lambda update-function-configuration \
  --function-name $FUNCTION_NAME \
  --handler lambda_handler.handler

echo "Updating Lambda code file for $FUNCTION_NAME..."
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://./$FUNCTION_NAME.zip
