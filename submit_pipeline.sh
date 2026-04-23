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

slideFiles=$(find /$AKOYA_ISILON/$PROJECT -name "*.qptiff" | wc -l)
readyFiles=$(($slideFiles-1))

mkdir -p $AKOYA_ISILON/$PROJECT/logs

JOB1=$(sbatch --parsable \
    --array=0-$readyFiles%3 \
    --output=$AKOYA_ISILON/$PROJECT/logs/ingestion_%A_%a.log \
    --error=$AKOYA_ISILON/$PROJECT/logs/ingestion_%A_%a.err \
    scripts/slurm/ingestion.sh $PROJECT)
JOB2=$(sbatch --parsable \
    --array=0-$readyFiles%3 \
    --output=$AKOYA_ISILON/$PROJECT/logs/preprocessing_%A_%a.log \
    --error=$AKOYA_ISILON/$PROJECT/logs/preprocessing_%A_%a.err \
    --dependency=afterok:$JOB1 scripts/slurm/preprocessing.sh $PROJECT)
JOB3=$(sbatch --parsable \
    --array=0-$readyFiles%3 \
    --output=$AKOYA_ISILON/$PROJECT/logs/segmentation_%A_%a.log \
    --error=$AKOYA_ISILON/$PROJECT/logs/segmentation_%A_%a.err \
    --dependency=afterok:$JOB2 scripts/slurm/segmentation.sh $PROJECT $DIAMETER)
JOB4=$(sbatch --parsable \
    --array=0-$readyFiles%3 \
    --output=$AKOYA_ISILON/$PROJECT/logs/feature_extraction_%A_%a.log \
    --error=$AKOYA_ISILON/$PROJECT/logs/feature_extraction_%A_%a.err \
    --dependency=afterok:$JOB3 scripts/slurm/feature_extraction.sh $PROJECT $PANEL_CONFIG $N_NEIGH)

echo "Pipeline submitted for project: $PROJECT"
echo "Job IDs: $JOB1 $JOB2 $JOB3 $JOB4"
