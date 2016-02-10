#! /bin/bash

# get guardian INJ package set
export GUARD_MODULE_PATH=${PWD}/../../lib

# make plot
guardutil graph -o guardian_inj.png INJ

