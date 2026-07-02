# =============================================================================
# anndata_export.py
# Author: Henry Boyes
# Institution: Cleveland Clinic
# Date: 3/11/2026
# Version: v0.3.0
# Contact: boyeshenry@gmail.com
# Description: This script takes the extracted cell features and intensities and converts them to .h5ad AnnData format for
# phenotyping and spatial analysis
# =============================================================================

import os
import anndata
import sqlite3
import numpy as np 
import pandas as pd 
import argparse
from utils import setup_logging
from datetime import datetime

ISILON_BASE = os.environ.get("AKOYA_ISILON")
DB_PATH = os.environ.get("AKOYA_DB")
SLURM_ARRAY = os.environ.get("SLURM_ARRAY_TASK_ID")
if SLURM_ARRAY:
    SLURM_ARRAY = int(SLURM_ARRAY)

parser = argparse.ArgumentParser(description="Project folder name")
parser.add_argument("--project", required=True, type=str, help="Enter the project folder name (case sensitive)")
args = parser.parse_args()

def get_slides(cursor, project):
    """
    This function checks the project for slides that have 'Passed' feature_extraction in in the pipeline_status

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

    cursor.execute(
        """Select s.slide_id, s.slide_name
        from slides s 
        join pipeline_status ps on
            s.slide_id = ps.slide_id
        where ps.feature_extraction = 'Passed'
        and ps.anndata_export != 'Complete'
        and s.file_path like ?""", (project_filter,)
    )
    res = cursor.fetchall()

    if res:
        res.sort(key=lambda x: x[0])
        return res
    else:
        print('No data found! Please check the database.')

def check_cell_counts(cursor, slide_id):
    """
    This function checks the cell counts from segmentation_results (expected) and cell_features (acutal). It compares them
    and creates a warning if the discrepancy is greater than 20%

    : ARGS :

    cursor : sqlite3.cursor
        Active database cursor for executing queries
    
    slide_id : int
        The integer primary key from the akoya.db

    
    : RETURNS :

    check_cells : float
        The ratio of estimated vs actually counted cells
    """
    cursor.execute("SELECT cell_count FROM segmentation_results where slide_id = ?", (slide_id,))
    seg_counts = cursor.fetchone()[0]

    cursor.execute("select count(*) from cell_features where slide_id = ?", (slide_id,))
    feat_counts = cursor.fetchone()[0]

    check_cells = feat_counts/seg_counts

    if check_cells < 0.80:
        cursor.execute("UPDATE pipeline_status SET notes = ? WHERE slide_id = ?",
                        ('Warning! Discrepancy in cell counts > 20%', slide_id))

    return check_cells

    
def fetch_cell_feat(cursor, slide_id):
    """
    This function retrieves the cell features from the database. It returns a DataFrame

    : ARGS : 

    cursor : sqlite3.cursor
        Active database cursor for executing queries
    
    slide_id : int
        The integer primary key from the akoya.db

    
    : RETURNS : 

    cell_feats_df : df
        A DataFrame of df of cell features
    """

    cursor.execute("select * from cell_features where slide_id = ?", (slide_id,))
    columns = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    cell_feat_df = pd.DataFrame(rows, columns=columns)

    return cell_feat_df

def fetch_cell_intensity(cursor, slide_id):
    """
    This function retrieves the channel intensities per cell from the database. It returns two DataFrames

    : ARGS : 

    cursor : sqlite3.cursor
        Active database cursor for executing queries
    
    slide_id : int
        The integer primary key from the akoya.db

    
    : RETURNS : 

    mean_intensity_df : df
        A DataFrame of df of mean channel intensities per cell
    
    max_intensity_df : df
        A DataFrame of df of max channel intensities per cell
    """

    cursor.execute("""SELECT ci.cell_id, ci.channel_name, ci.mean_intensity, ci.max_intensity
                    from cell_intensity ci
                    join cell_features cf on
                        ci.cell_id = cf.cell_id
                    where cf.slide_id = ?""", (slide_id,))
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()

    intensity_df = pd.DataFrame(rows, columns=cols)
    intensity_df['mean_intensity'] = intensity_df['mean_intensity'].apply(lambda x: float(x) if not isinstance(x, float) else x)
    intensity_df['max_intensity'] = intensity_df['max_intensity'].apply(lambda x: float(x) if not isinstance(x, float) else x)

    mean_intensity_df = pd.pivot_table(intensity_df, index='cell_id', \
        columns='channel_name', values='mean_intensity')
    
    max_intensity_df = pd.pivot_table(intensity_df, index='cell_id', \
        columns='channel_name', values='max_intensity')

    return mean_intensity_df, max_intensity_df

def fetch_channel_metadata(cursor, slide_id):
    """
    This function fetches the channel metadata from the database. It returns a DataFrame
    
    : ARGS : 

    cursor : sqlite3.cursor
        Active database cursor for executing queries
    
    slide_id : int
        The integer primary key from the akoya.db

    : RETURNS :

    meta_df : df
        A DataFrame of the channel metadata
    
    """
    
    cursor.execute("""Select channel_name, min_intensity, max_intensity,
                    mean_intensity, nonzero_fraction, flagged, flag_message
                    from channel_stats
                    where slide_id = ?""", (slide_id,))
    cols = [d[0] for d in cursor.description]
    meta_df = pd.DataFrame(cursor.fetchall(), columns=cols)


    meta_df = meta_df.replace(b'\x00\x00', None)
    meta_df = meta_df.replace('', None)
    
    meta_df = meta_df.fillna({'flag_message': '', 'flagged': 0})


    return meta_df

def build_anndata(features, mean_intensity, max_intensity, channel_meta, slide_id, slide_name):
    """
     This function takes the dataframes returned from the other functions in this script and assembles them as an AnnData object
     to be saved as a .h5ad file

     : ARGS : 

     features : df
        The cell features df created by fetch_cell_features

    mean_intensity : df
        The mean cell intensity per channel from fetch_cell_intensity

    max_intensity : df
        The maximum cell intensity per channel from fetch_cell_intensity

    channel_meta : df
        The channel metadata from fetch_channel_metadata

    slide_id : int
        The integer number for slide_id

    slide_name : str
        The name of the slide

    
    : RETURNS : 

    adata : obj
        An AnnData object, ready to be converted into a .h5ad file
    """

    cell_feat_df = features.set_index('cell_id').reindex(mean_intensity.index)
    cell_feat_df['slide_id'] = slide_id
    cell_feat_df['slide_name'] = slide_name


    adata = anndata.AnnData(
        X=mean_intensity.to_numpy(),
        obs=cell_feat_df,
        var=channel_meta.set_index('channel_name'),
    )

    adata.layers['max_intensity'] = max_intensity.to_numpy()
    adata.obsm['spatial'] = cell_feat_df[['centroid_x', 'centroid_y']].to_numpy()

    return adata


def update_status(cursor, slide_id, status, notes):
    """
    This function updates anndata_export pipeline_status in the db

    : ARGS :

    cursor : sqlite3.cursor
        Active database cursor for executing queries
    
    slide_id : int
        The integer primary key from the akoya.db

    status : str
        The status of the export

    notes : str
        The warning status/notes associated with the export
    """

    cursor.execute("UPDATE pipeline_status SET anndata_export = ? WHERE slide_id = ?", (status, slide_id))
    cursor.execute("SELECT notes FROM pipeline_status WHERE slide_id = ?", (slide_id,))
    existing_notes = cursor.fetchone()[0]

    if notes == None:
        combined_notes = existing_notes
    elif existing_notes:
        combined_notes = f"{existing_notes} | {notes}"
    else:
        combined_notes = notes
    
    cursor.execute("UPDATE pipeline_status SET notes = ? WHERE slide_id = ?", (combined_notes, slide_id))

    return

def validate_adata(adata):
    """
    This function checks to ensure that the adata object has data stored in it

    : ARGS : 

    adata : AnnData obj
        The AnnData object created to save as a .h5ad file

    : RETURNS : 

    status : bool
        A bool on the status of the validation
    """

    if np.any(np.all(adata.X == 0, axis=1)):
        print("adata.X has a row of all zeros")
        return False
    if not len(adata.X) == len(adata.obs):
        print("adata.X and adata.obs rows do not match")
        return False
    if not adata.X.shape[1] == len(adata.var):
        print("adata.X.shape[1] and adata.var columns do not match")
        return False

    return True


if __name__ == "__main__":
    start_time = datetime.now()
    folder_name = args.project
    db_path = DB_PATH
    project_path = f"{ISILON_BASE}/{folder_name}"


    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    log_dir = os.path.join(project_path, 'logs')

    logger = setup_logging(folder_name, log_dir)

    project_path = f"{ISILON_BASE}/{folder_name}"
    anndata_dir = os.path.join(project_path, 'anndata')
    os.makedirs(anndata_dir, exist_ok=True)
    logger.info(f"AnnData directory ready: {anndata_dir}")

    logger.info("Fetching slides")
    slides = get_slides(cursor, folder_name)
    if not slides:
        exit()

    logger.info("Compiling data")

    if SLURM_ARRAY:
        slides = [slides[SLURM_ARRAY]]
    
    for slide_id, slide_name in slides:
        try:
            count = check_cell_counts(cursor, slide_id)
            feat = fetch_cell_feat(cursor, slide_id)
            intensity = fetch_cell_intensity(cursor, slide_id)
            meta = fetch_channel_metadata(cursor, slide_id)
            data = build_anndata(feat, intensity[0], intensity[1], meta, slide_id, slide_name)
            if validate_adata(data):
                output_path = os.path.join(anndata_dir, f"slide_{slide_id}_{slide_name}.h5ad")
                data.write_h5ad(output_path)
                status = 'Complete'
                update_status(cursor, slide_id, status, None)

                
            else:
                status = 'Failed'
                update_status(cursor, slide_id, status, None)
                logger.error(f"Slide {slide_id} failed!")
        except Exception as e:
            logger.error(f"Slide {slide_name} failed", exc_info=True)
    
    conn.commit()
    conn.close()

    end_time = datetime.now() - start_time
    logger.info(f"Done! Finished in {end_time}")
    