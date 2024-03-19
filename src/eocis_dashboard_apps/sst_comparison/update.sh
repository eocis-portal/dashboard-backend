#!/bin/bash

deployment_folder=$1

python calc_globsst.py /data/esacci_sst/public/CDR3.0_release/Analysis/L4/v3.0.1 -o globmeansst.nc --update

python preprocess.py --input-path globmeansst.nc --variable-name analysed_sst --output-path $deployment_folder/globmeansst.csv

