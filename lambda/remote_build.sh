#!/bin/bash

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
mkdir -p build/bin
cd build

# Copy all packages, including any hidden dotfiles.
cp -rT /home/ec2-user/pshtt/lib/python3.6/site-packages/ .
cp -rT /home/ec2-user/pshtt/lib64/python3.6/site-packages/ .
# Copy the pshtt binary
cp /home/ec2-user/pshtt/bin/pshtt bin/

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
