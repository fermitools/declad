#!/bin/sh

# find the software
# . /path/to/virtualenv/activate
#
# or
version=2.0.4
if [ "$1" == "-d" ]
then
    version=develop
fi

. $HOME/packages/setup-env.sh
spack load declad@${version}

export METACAT_SERVER_URL=https://metacat.xxxx.yyy:9443/hypot_meta_prod/app
export PYTHONPATH=$HOME:$PYTHONPATH
export RUCIO_HOME=$HOME/rucio_config
export PATH=$(spack location -i declad@${version}):$HOME/bin:$PATH

# we should be using our managed token refreshed by our refresh script
# for copies, etc.
export X509_CERT_DIR=/etc/grid-security/certificates

nohup declad.py -dc declad_config.yaml  < /dev/null > logs/nohup.out 2>&1 &
echo $! > logs/declad.pid
