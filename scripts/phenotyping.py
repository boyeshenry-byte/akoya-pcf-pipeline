# =============================================================================
# phenotyping.py
# Author: Henry Boyes
# Institution: Cleveland Clinic
# Date: 3/16/2026
# Version: v0.4.1
# Contact: boyeshenry@gmail.com
# Description: This script takes the AnnData files and preprocesses them, performs Leiden clustering, and UMAP embedding. 
# It then plots the UMAP data based on marker and cluster. It creates a heatmap based on the clustering and save the figures.
# =============================================================================

import os
import argparse
import numpy as np 
import sqlite3
import json
import anndata as ad 
import scanpy as sc 
from utils import setup_logging
from datetime import datetime

ISILON_BASE = os.environ.get("AKOYA_ISILON")
DB_PATH = os.environ.get("AKOYA_DB")
SLURM_ARRAY = os.environ.get("SLURM_ARRAY_TASK_ID")
if SLURM_ARRAY:
    SLURM_ARRAY = int(SLURM_ARRAY)

parser = argparse.ArgumentParser(description="Project folder name")
parser.add_argument("--project", required=True, type=str, help="Enter the project folder name (case sensitive)")
parser.add_argument("--panel_config", default="configs/io60_panel_config.json", type=str, 
help="Path to panel config JSON for cluster annotation")
args = parser.parse_args()

def find_slides(cursor, project):
    """
    This function checks if a slide has been completed anndata_export. It returns a tuple of slide_id and slide_name

    : ARGS :

    cursor : sqlite3.cursor
        Active database cursor for executing queries

    project : str
        The project/dir name, given by argparse

    
    : RETURNS :

    res : list
        A list of tuples of slide_id and slide_name for the project
    """

    project_filter = f"%{project}%"

    cursor.execute("""SELECT s.slide_id, s.slide_name
    FROM slides s
    JOIN pipeline_status ps ON
        s.slide_id = ps.slide_id
    where ps.anndata_export ='Complete'
    AND ps.phenotyping != 'Complete'
    AND s.file_path LIKE ?;""", (project_filter,))

    res = cursor.fetchall()

    if res:
        res.sort(key=lambda x: x[0])
        return res
    else:
        print('No data found! Please check the database.')

def preprocess(adata):
    """
    This function stores the copy raw AnnData values, the normalizes the values using arcsinh with a cofactor of 5.

    : ARGS : 
    
    adata : AnnData object
        An imported .h5ad file

    : RETURNS : 

    adata : AnnData object
        A preprocessed AnnData file
    """

    cofactor = 5

    adata.raw = adata
    adata.X = np.arcsinh(adata.X/cofactor)

    return adata

def dimension_reduction(adata):
    """
    This function applies PCA reduction and neighbors graphing to the AnnData object

    : ARGS : 

    adata : AnnData object
        The preprocessed AnnData object

    : RETURNS : 

    adata : AnnData object
        An AnnData object with PCA reduction and neighbors graphing added
    """

    sc.pp.pca(adata)
    sc.pp.neighbors(adata)

    return adata

def cluster(adata):
    """
    This function clusters the AnnData using Leiden clustering. It uses a default resolution of 0.5

    : ARGS : 

    adata : AnnData object
        The reduced AnnData object from dimension_reduction

    : RETURNS :

    adata : AnnData object
        An AnnData object with clustering applied
    """

    sc.tl.leiden(adata, resolution=0.5, flavor='igraph', n_iterations=2, directed=False) #using default args

    return adata

def annotate_clusters(adata, panel_config):
    """
    This function suggests annotations for the Leiden clusters based on the provided panel configuration

    : ARGS :

    adata : AnnData object
        An AnnData object that has had Leiden clustering applied

    panel_config : .JSON file
        A .JSON file provided for annotation. Default is the IO60 panel

    : RETURNS :

    adata : AnnData object
        An AnnData object with suggested annotations applied to the clusters
    """

    with open(panel_config, 'r') as f:
        panel = json.load(f)

    marker_lookup = {}

    for category, markers in panel.items():
        for marker, cell_type in markers.items():
            marker_lookup[marker] = cell_type

    agg = sc.get.aggregate(adata, by='leiden', func='mean')

    annotations = {}

    for cluster, expression in zip(agg.obs_names, agg.X):
        top_marker = agg.var_names[np.argmax(expression)]
        cell_type = marker_lookup.get(top_marker, "unknown")
        annotations[cluster] = cell_type

    adata.obs['cell_type_suggested'] = adata.obs['leiden'].map(annotations)

    return adata


def embed(adata):
    """
    This function embeds the UMAP data in the AnnData object

    : ARGS :

    adata : AnnData object
        The AnnData object that has neighbor_graphing and annotations applied 

    : RETURNS :

    adata : AnnData object
        The AnnData object with UMAP embeded
    """

    sc.tl.umap(adata)

    return adata

def qc_plot(adata, output_dir, slide_id):
    """
    This function  plots a UMAP colored by Leiden clusters, a UMAP colored by marker, and a heatmap per cluster. 
    It then saves them to the dir

    : ARGS : 

    adata : AnnData object
        An AnnData object that has UMAP embeded

    output_dir : str
        A str to the output dir
    """

    sc.settings.figdir = output_dir

    sc.pl.umap(adata, color='leiden', save=f'slide{slide_id}_leiden.png', show=False)

    sc.pl.umap(adata, color='cell_type_suggested', save=f'_slide{slide_id}_cell_type_suggested.png', show=False)

    sc.pl.umap(adata, color=adata.var_names.tolist(), save=f'_slide{slide_id}_markers.png', show=False)

    sc.pl.heatmap(adata, var_names=adata.var_names.tolist(), groupby='leiden', save=f'_slide{slide_id}.png', show=False)

    return

def update_pipeline_status(cursor, status, slide_id):
    """
    This function updates the pipelines status

    : ARGS : 

    cursor : sqlite3.cursor
        Active database cursor for executing queries
    
    slide_id : int
        The integer primary key from the akoya.db
    """

    cursor.execute("UPDATE pipeline_status SET phenotyping = ? WHERE slide_id = ?", (status, slide_id))

    return

if __name__ == "__main__":
    start_time = datetime.now()
    folder_name = args.project
    db_path = DB_PATH
    project_path = f"{ISILON_BASE}/{folder_name}"

    log_dir = os.path.join(project_path, 'logs')

    logger = setup_logging(folder_name, log_dir)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    phenotyping_dir = os.path.join(project_path, 'phenotyping')
    figures_dir = os.path.join(phenotyping_dir, 'figures')
    os.makedirs(phenotyping_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)
    logger.info(f"Figure directory ready: {figures_dir}")

    logger.info("Fetching slides")
    slides = find_slides(cursor, folder_name)
    if not slides:
        exit()

    if SLURM_ARRAY:
        slides = [slides[SLURM_ARRAY]]
    
    for slide in slides:
        try:
            slide_id, slide_name = slide
            file_path = os.path.join(project_path, 'anndata', f"slide_{slide_id}_{slide_name}.h5ad")
            adata = ad.read_h5ad(file_path)

            logger.info(f"Phenotyping slide {slide_id}")

            adata = preprocess(adata)
            adata = dimension_reduction(adata)
            adata = cluster(adata)
            adata = annotate_clusters(adata, args.panel_config)
            adata = embed(adata)
            qc_plot(adata, figures_dir, slide_id)
            
            output_path = os.path.join(phenotyping_dir, f"slide_{slide_id}_{slide_name}_phenotyped.h5ad")
            adata.write_h5ad(output_path)

            status = 'Complete'
        
            update_pipeline_status(cursor, status, slide_id)
        
        except Exception as e:

            status = 'Failed'

            update_pipeline_status(cursor, status, slide_id)
            logger.error(f"Slide {slide_id} failed", exc_info=True)

    conn.commit()
    conn.close()
    
    end_time  = datetime.now() - start_time
    logger.info(f"Done! Finished in {end_time}")