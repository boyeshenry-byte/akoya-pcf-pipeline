#!/bin/bash

#SBATCH --job-name=akoya_segmentation
#SBATCH --gres=gpu:1
#SBATCH --partition=gpu-a100
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G

/opt/python/3.11.3/bin/python scripts/segmentation.py --project $1 --diameter $2