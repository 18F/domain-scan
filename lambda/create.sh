#!/bin/bash

##
# Create a Lambda function from a zip file.

SCANNER_NAME=$1
FUNCTION_NAME="task_$SCANNER_NAME"

echo "Creating function: $FUNCTION_NAME"

# Region and credentials set externally.
# $AWS_LAMBDA_ROLE is a Role ARN.
aws lambda create-function \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://./$FUNCTION_NAME.zip \
  --role $AWS_LAMBDA_ROLE \
  --handler lambda_handler.handler \
  --runtime python3.6 \
  --timeout 30 \
  --memory-size 128

