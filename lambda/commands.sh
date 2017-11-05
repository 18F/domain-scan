##
# Collection of commands, not meant to be run directly.

# Region and credentials set externally.
# $AWS_LAMBDA_ROLE is a Role ARN.
aws lambda create-function \
  --function-name pshtt_test \
  --zip-file fileb://./pshtt_test.zip \
  --role $AWS_LAMBDA_ROLE \
  --handler pshtt_test.handler \
  --runtime python3.6 \
  --timeout 10 \
  --memory-size 128

# Update a function config in-place.
aws lambda update-function-configuration \
   --function-name pshtt_test  \
   --handler pshtt_test.handler

# On an Amazon Linux box, to set up.

sudo yum install python36 python36-virtualenv
sudo yum install gcc libffi-devel openssl-devel

virtualenv-3.6 pshtt
source pshtt/bin/activate
pip install pshtt


