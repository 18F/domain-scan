#!/bin/bash

# From the lambda dir - use the build/ dir to assemble a zip
# and "publish" it back up to the lambda dir.
mkdir -p build
cd build
rm -r * # clean it up

# Copy the actual used .py files into the build.
cp ../pshtt_test.py .

# Not used: local virtualenv.
# cp -r $HOME/.virtualenvs/lambda/lib/python3.6/site-packages/* .

# Used: Remote virtualenv (needs to be prepped at venv.zip)
echo "Downloading AMI-built virtualenv..."
scp -r lambda:/home/ec2-user/venv.zip .
unzip -q venv.zip
rm venv.zip

echo "Building zip package..."
zip -rq9 ../pshtt_test.zip .
cd ..

# Update the function's code with the latest zipped code.
echo "Publishing to Lambda..."
aws lambda update-function-code \
  --function-name pshtt_test \
  --zip-file fileb://./pshtt_test.zip
