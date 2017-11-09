#!/bin/bash

##
# Update a Lambda function in-place.

FUNCTION_NAME=$1

echo "Creating function: $FUNCTION_NAME"

aws lambda update-function-configuration \
   --function-name $FUNCTION_NAME  \
   --timeout 300