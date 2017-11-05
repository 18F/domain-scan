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
  --timeout 30 \
  --memory-size 128

# Update a function config in-place.
aws lambda update-function-configuration \
   --function-name pshtt_test  \
   --timeout 45

# On an Amazon Linux box, to initially set up.
sudo yum install python36 python36-virtualenv
sudo yum install gcc libffi-devel openssl-devel
virtualenv-3.6 pshtt
source pshtt/bin/activate
pip install pshtt
deactivate

# Prepare the virtualenv for ease of integration into remote build.
rm venv.zip # if it exists
cd build
cp -r /home/ec2-user/pshtt/lib/python3.6/site-packages/* .
cp -r /home/ec2-user/pshtt/lib64/python3.6/site-packages/* .
zip -rq9 ../venv.zip *
cd ..
