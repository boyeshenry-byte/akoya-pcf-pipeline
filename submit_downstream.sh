#!/bin/bash

while [[ $# -gt 0 ]]; do
    case $1 in
        --project)
            PROJECT="$2"
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
        --stage)
            STAGE="$2"
            shift 2
            ;;
    esac

done

if [[ -z "$PROJECT" ]]; then
    echo "USAGE: bash submit_downstream.sh --project <project_name> [--n_neigh <value>]"
    exit 1
fi

if [[ -z "$STAGE" ]]; then
    echo "USAGE: bash submit_downstream.sh --stage"
    exit 1
fi

case $STAGE in
    anndata_export)
        dbCount=$(sqlite3 $AKOYA_DB "Select count(s.slide_id)
        from slides s 
        join pipeline_status ps on
            s.slide_id = ps.slide_id
        where ps.feature_extraction = 'Passed'
        and ps.anndata_export != 'Complete'
        and s.file_path like '%$PROJECT%'")

        JOB5=$( sbatch --parsable \
        --array=0-$(($dbCount-1)) \
        --output=$AKOYA_ISILON/$PROJECT/logs/anndata_export_%A_%a.log \
        --error=$AKOYA_ISILON/$PROJECT/logs/anndata_export_%A_%a.err \
        scripts/slurm/anndata_export.sh $PROJECT)
        ;;
    phenotyping)
        dbCount=$(sqlite3 $AKOYA_DB "Select count(s.slide_id)
        from slides s 
        join pipeline_status ps on
            s.slide_id = ps.slide_id
        where ps.anndata_export = 'Complete'
        and ps.phenotyping !='Complete'
        and s.file_path like '%$PROJECT%'")

        JOB6=$( sbatch --parsable \
        --array=0-$(($dbCount-1)) \
        --output=$AKOYA_ISILON/$PROJECT/logs/phenotyping_%A_%a.log \
        --error=$AKOYA_ISILON/$PROJECT/logs/phenotyping_%A_%a.err \
        scripts/slurm/phenotyping.sh $PROJECT $PANEL_CONFIG)
        ;;
    spatial_analysis)
        dbCount=$(sqlite3 $AKOYA_DB "Select count(s.slide_id)
        from slides s 
        join pipeline_status ps on
            s.slide_id = ps.slide_id
        where ps.phenotyping ='Complete'
        and ps.spatial_analysis != 'Complete'
        and s.file_path like '%$PROJECT%'")

        JOB7=$( sbatch --parsable \
        --array=0-$(($dbCount-1)) \
        --output=$AKOYA_ISILON/$PROJECT/logs/spatial_analysis_%A_%a.log \
        --error=$AKOYA_ISILON/$PROJECT/logs/spatial_analysis_%A_%a.err \
        scripts/slurm/spatial_analysis.sh $PROJECT $N_NEIGH)
        ;;

    generate_report)
        JOB8=$( sbatch --parsable \
                --output=$AKOYA_ISILON/$PROJECT/logs/generate_report_%j.log \
                --error=$AKOYA_ISILON/$PROJECT/logs/generate_report_%j.err \
                scripts/slurm/generate_report.sh $PROJECT)
                ;;

esac