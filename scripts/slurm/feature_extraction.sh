#!/bin/bash

#SBATCH --job-name=akoya_feature_extration
#SBATCh --partition=defq
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G

/opt/python/3.11.3/bin/python scripts/feature_extration.py --project $1