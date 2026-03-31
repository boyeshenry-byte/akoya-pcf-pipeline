#!/bin/bash

#SBATCH --job-name=akoya_spatial_analysis
#SBATCH --partition=defq
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G

/opt/python/3.11.3/bin/python scripts/spatial_analysis.py --project $1 --n_neigh $2