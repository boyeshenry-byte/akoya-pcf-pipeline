#!/bin/bash

#SBATCH --job-name=akoya_preprocessing
#SBATCH --partition=defq
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G

if [[ -n "$2" ]]; then
    /opt/python/3.11.3/bin/python scripts/preprocessing.py --project $1 --sigma $2
else
    /opt/python/3.11.3/bin/python scripts/preprocessing.py --project $1
fi