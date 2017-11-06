##
# Collection of commands, not meant to be run directly.

export FUNCTION_NAME=sslyze_test

# Region and credentials set externally.
# $AWS_LAMBDA_ROLE is a Role ARN.
aws lambda create-function \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://./$FUNCTION_NAME.zip \
  --role $AWS_LAMBDA_ROLE \
  --handler $FUNCTION_NAME.handler \
  --runtime python3.6 \
  --timeout 30 \
  --memory-size 128

# Update a function config in-place.
aws lambda update-function-configuration \
   --function-name $FUNCTION_NAME  \
   --timeout 45

