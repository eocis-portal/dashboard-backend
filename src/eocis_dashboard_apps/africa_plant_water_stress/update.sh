#!/bin/bash

deployment_folder=$1

thisdir=`dirname $0`

python update.py --deployment-dolder $deployment_folder