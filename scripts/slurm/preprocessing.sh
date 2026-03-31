#!/bin/bash

#SBATCH --job-name=akoya_preprocessing
#SBATCH --partition=defq
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G

/opt/python/3.11.3/bin/python scripts/preprocessing.py --project $1