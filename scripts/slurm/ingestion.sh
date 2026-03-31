#!/bin/bash

#SBATCH --job-name=akoya_ingestion
#SBATCH --partition=defq
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G

/opt/python/3.11.3/bin/python scripts/ingestion.py --project $1