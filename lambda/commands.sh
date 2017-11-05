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
sudo yum install sqlite-devel gcc libffi-devel openssl-devel
virtualenv-3.6 pshtt
source pshtt/bin/activate
pip install pshtt
deactivate

###
# Routine builds.

# Prepare the virtualenv for ease of integration into remote build.
rm venv.zip # if it exists
rm -r build # clean
mkdir -p build
cd build

# Copy all packages, including any hidden dotfiles.
cp -rT /home/ec2-user/pshtt/lib/python3.6/site-packages/ .
cp -rT /home/ec2-user/pshtt/lib64/python3.6/site-packages/ .

# Lambda workaround for SQLite.
wget https://github.com/Miserlou/lambda-packages/raw/master/lambda_packages/sqlite3/python3.6-sqlite3-3.6.0.tar.gz
tar -zxvf python3.6-sqlite3-3.6.0.tar.gz
rm python3.6-sqlite3-3.6.0.tar.gz

# Lambda workaround for cryptography (Lambda doesn't have openssl 1.0.2)
rm -r cryptography/
rm -r cryptography-1.9-py3.6.egg-info/
wget https://github.com/Miserlou/lambda-packages/raw/master/lambda_packages/cryptography/python3.6-cryptography-1.9.tar.gz
tar -zxvf python3.6-cryptography-1.9.tar.gz
rm python3.6-cryptography-1.9.tar.gz

zip -rq9 ../venv.zip .
cd ..
