#!/bin/bash

#SBATCH --job-name=akoya_feature_extraction
#SBATCH --partition=defq
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G

/opt/python/3.11.3/bin/python scripts/feature_extraction.py --project $1

submit_downstream.sh --project $1 --panel_config $2 --n_neigh $3 --stage anndata_export