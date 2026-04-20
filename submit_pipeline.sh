#!/bin/bash

DIAMETER=None
N_NEIGH=10
PANEL_CONFIG="configs/io60_panel_config.json"

while [[ $# -gt 0 ]]; do
    case $1 in
        --project)
            PROJECT="$2"
            shift 2
            ;;
        --diameter)
            DIAMETER="$2"
            shift 2
            ;;
        --n_neigh)
            N_NEIGH="$2"
            shift 2
            ;;
        --panel_config)
            PANEL_CONFIG="$2"
            shift 2
            ;;
    esac

done

if [[ -z "$PROJECT" ]]; then
    echo "USAGE: bash submit_pipeline.sh --project <project_name> [--diameter <value>] [--n_neigh <value>]"
    exit 1
fi

mkdir -p $AKOYA_ISILON/$PROJECT/logs

JOB1=$(sbatch --parsable \
    --output=$AKOYA_ISILON/$PROJECT/logs/ingestion_%j.log \
    --error=$AKOYA_ISILON/$PROJECT/logs/ingestion_%j.err \
    scripts/slurm/ingestion.sh $PROJECT)
JOB2=$(sbatch --parsable \
    --output=$AKOYA_ISILON/$PROJECT/logs/preprocessing_%j.log \
    --error=$AKOYA_ISILON/$PROJECT/logs/preprocessing_%j.err \
    --dependency=afterok:$JOB1 scripts/slurm/preprocessing.sh $PROJECT)
JOB3=$(sbatch --parsable \
    --output=$AKOYA_ISILON/$PROJECT/logs/segmentation_%j.log \
    --error=$AKOYA_ISILON/$PROJECT/logs/segmentation_%j.err \
    --dependency=afterok:$JOB2 scripts/slurm/segmentation.sh $PROJECT $DIAMETER)
JOB4=$(sbatch --parsable \
    --output=$AKOYA_ISILON/$PROJECT/logs/feature_extraction_%j.log \
    --error=$AKOYA_ISILON/$PROJECT/logs/feature_extraction_%j.err \
    --dependency=afterok:$JOB3 scripts/slurm/feature_extraction.sh $PROJECT)
JOB5=$(sbatch --parsable \
    --output=$AKOYA_ISILON/$PROJECT/logs/anndata_export_%j.log \
    --error=$AKOYA_ISILON/$PROJECT/logs/anndata_export_%j.err \
    --dependency=afterok:$JOB4 scripts/slurm/anndata_export.sh $PROJECT)
JOB6=$(sbatch --parsable \
    --output=$AKOYA_ISILON/$PROJECT/logs/phenotyping_%j.log \
    --error=$AKOYA_ISILON/$PROJECT/logs/phenotyping_%j.err \
    --dependency=afterok:$JOB5 scripts/slurm/phenotyping.sh $PROJECT $PANEL_CONFIG)
JOB7=$(sbatch --parsable \
    --output=$AKOYA_ISILON/$PROJECT/logs/spatial_analysis_%j.log \
    --error=$AKOYA_ISILON/$PROJECT/logs/spatial_analysis_%j.err \
    --dependency=afterok:$JOB6 scripts/slurm/spatial_analysis.sh $PROJECT $N_NEIGH)
JOB8=$(sbatch --parsable \
    --output=$AKOYA_ISILON/$PROJECT/logs/generate_report_%j.log \
    --error=$AKOYA_ISILON/$PROJECT/logs/generate_report_%j.err \
    --dependency=afterok:$JOB7 scripts/slurm/generate_report.sh $PROJECT)

echo "Pipeline submitted for project: $PROJECT"
echo "Job IDs: $JOB1 $JOB2 $JOB3 $JOB4 $JOB5 $JOB6 $JOB7 $JOB8"
