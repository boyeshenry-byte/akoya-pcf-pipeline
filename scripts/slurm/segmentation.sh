#!/bin/bash

#SBATCH --job-name=akoya_segmentation
#SBATCH --partition=xtreme
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem-per-cpu=30000

/opt/python/3.11.3/bin/python scripts/segmentation.py --project $1 --diameter $2