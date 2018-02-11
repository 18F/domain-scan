#!/bin/bash

#########################################
# One-time Amazon Linux setup.
#########################################

# System deps.
sudo yum install python36 python36-virtualenv \
     sqlite-devel gcc libffi-devel openssl-devel \
     git wget zip


#########################################
# Repeatable from here.
#########################################

VENV=chrome-env

rm -r $VENV
virtualenv-3.6 $VENV
source $VENV/bin/activate

# TODO: move to requirements-lambda.txt or some other thing
pip install strict-rfc3339 publicsuffix

deactivate

###
# Routine builds.

# Prepare the virtualenv for ease of integration into remote build.
rm venv.zip # if it exists
rm -r build # clean
mkdir -p build
mkdir -p build/bin
cd build

# Copy chrome headless.
cp ../chrome-packaged/headless_shell .

# Copy all packages, including any hidden dotfiles.
cp -rT /home/ec2-user/$VENV/lib/python3.6/site-packages/ .
cp -rT /home/ec2-user/$VENV/lib64/python3.6/site-packages/ .

# Remove unneeded aspects of the virtualenv.
rm -r pip pkg_resources wheel pip-*-info wheel-*-info setuptools setuptools-*-info

zip -rq9 ../venv.zip .
cd ..
