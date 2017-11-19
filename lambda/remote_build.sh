#!/bin/bash

#########################################
# One-time Amazon Linux setup.
#########################################

# System deps.
sudo yum install python36 python36-virtualenv
sudo yum install sqlite-devel gcc libffi-devel openssl-devel
sudo yum install git

# domain-scan isn't in PyPi.
git clone https://github.com/18F/domain-scan
# pshtt is in PyPi, but often lags behind.
git clone https://github.com/dhs-ncats/pshtt

#########################################
# If testing out a branch of domain-scan
# or pshtt, add git instructions here.
#########################################

# cd pshtt
# git checkout branch-name

#########################################
# Repeatable from here.
#########################################

rm -r scan-env
virtualenv-3.6 scan-env
source scan-env/bin/activate

cd pshtt
pip install .
cd ..

cd domain-scan
pip install -r requirements.txt
cd ..

deactivate

###
# Routine builds.

# Prepare the virtualenv for ease of integration into remote build.
rm venv.zip # if it exists
rm -r build # clean
mkdir -p build
mkdir -p build/bin
cd build

VENV=scan-env

# Copy in a snapshot of the public suffix list in .txt form.
# Need to find a more managed way to store this.
cp /home/ec2-user/public-suffix-list.txt .

# Copy all packages, including any hidden dotfiles.
cp -rT /home/ec2-user/$VENV/lib/python3.6/site-packages/ .
cp -rT /home/ec2-user/$VENV/lib64/python3.6/site-packages/ .
# Copy the pshtt binary
cp /home/ec2-user/$VENV/bin/pshtt bin/

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
