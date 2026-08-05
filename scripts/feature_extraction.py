# =============================================================================
# feature_extraction.py
# Author: Henry Boyes
# Institution: Cleveland Clinic
# Date: 3/5/2026
# Contact: boyeshenry@gmail.com
# Description: This script takes in mask files created by segmenting .tiff files from the Akoya PCF. It extracts the cell features
# and intensities then writes them to a database for spatial analysis.
# =============================================================================

import os
import numpy as np
import sqlite3
import tifffile
import argparse
import xml.etree.ElementTree as ET
from skimage.measure import regionprops
from datetime import datetime
from ingestion import scan_for_files
from utils import is_already_processed, setup_logging

ISILON_BASE = os.environ.get("AKOYA_ISILON")
DB_PATH = os.environ.get("AKOYA_DB")
SLURM_ARRAY = os.environ.get("SLURM_ARRAY_TASK_ID")
if SLURM_ARRAY:
    SLURM_ARRAY = int(SLURM_ARRAY)

def extract_morphology(mask):
    """
    This function takes in a mask, generated from segmentation.py. It extracts the features of the cell morphology.
    It returns a list of dicts for each cell in the mask.

    : ARGS : 

    mask : array
        A "mask" array, generated from segmentation.py

    : RETURNS :

    res : list
        A list of dicts containing the features of each cell in the mask

    """

    res = []
    props = regionprops(mask)

    for prop in props:
        feat_dict = {
            'label' : prop.label,
            'area': prop.area,
            'centroid_x': prop.centroid[1],
            'centroid_y': prop.centroid[0],
            'eccentricity': prop.eccentricity,
            'perimeter': prop.perimeter,
            'solidity': prop.solidity
        }

        res.append(feat_dict)
    
    return res

def extract_intensity(mask, file_path):
    """
    This function takes in a mask, generated from segmentation.py. It extracts the features of the channel intensity and pairs it with
    a channel from file_path. It returns a list of dicts for each cell in the mask.

    : ARGS : 

    mask : array
        A "mask" array, generated from segmentation.py

    : RETURNS :

    res : list
        A list of dicts containing the intensities of each cell in the mask for the channels
    """

    res = []
    
    with tifffile.TiffFile(file_path) as tif:
        shaped = tif.shaped_metadata
        if shaped and 'Channel' in shaped[0]:
            channel_names_list = shaped[0]['Channel']['Name']
        else:
            channel_names_list = None
        for i, page in enumerate(tif.series[0].pages):
            channel_array = page.asarray()
            try:
                meta = ET.fromstring(page.description)
                name = meta.find('Name')
                channel_name = name.text if name is not None else None
            except (ET.ParseError, AttributeError):
                channel_name = channel_names_list[i] if channel_names_list else None
            
            # Verify channel names save with updated imagej format
            logger.info(f"Channel {i}: {channel_name}")

            props = regionprops(mask, channel_array)

            for prop in props:    
                intensity_dict = {
                    'channel_name': channel_name,
                    'channel_index': i,
                    'label': prop.label,
                    'mean_intensity': float(prop.intensity_mean),
                    'max_intensity': float(prop.intensity_max)
                }

                res.append(intensity_dict)

    return res

def write_morphology(db_path, file_path, cell_features):
    """
    This function writes the results of extract_morphology to the database.

    : ARGS :

    db_path : str
        The path to the database
    
    file_path : str
        The path to the original .QPTIFF

    cell_features : list
        A list of dicts from extract_morphology
    """

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Look up slide_id by file path
    cursor.execute("SELECT slide_id FROM slides WHERE file_path = ?", (file_path,))
    row = cursor.fetchone()

    if row is None:
        print(f"No slide found for {file_path}")
        conn.close()
        return

    slide_id = row[0]
    
    try: 
        for cell in cell_features:
            cursor.execute("""INSERT INTO cell_features
                (slide_id, label, area, centroid_x, 
                centroid_y, eccentricity, perimeter, solidity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (slide_id, cell['label'], cell['area'], cell['centroid_x'],
                cell['centroid_y'], cell['eccentricity'], cell['perimeter'], cell['solidity']))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

def write_intensity(db_path, file_path, intensity_features):
    """
    This function writes the results of extract_intensity to the database.

    : ARGS :

    db_path : str
        The path to the database
    
    file_path : str
        The path to the original .QPTIFF

    intensity_features : list
        A list of dicts from extract_intensity
    """

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Look up slide_id by file path
    cursor.execute("SELECT slide_id FROM slides WHERE file_path = ?", (file_path,))
    row = cursor.fetchone()
    
    if row is None:
        print(f"No slide found for {file_path}")
        conn.close()
        return

    slide_id = row[0]

    cursor.execute("SELECT label, cell_id FROM cell_features WHERE slide_id = ?", (slide_id,))
    label_to_cell_id = {row[0]: row[1] for row in cursor.fetchall()}

    status = "Passed"

    try: 
        for cell in intensity_features:
            cell_id = label_to_cell_id[cell['label']]
            cursor.execute("""INSERT INTO cell_intensity
                (cell_id, channel_index, channel_name, mean_intensity, max_intensity)
                VALUES (?, ?, ?, ?, ?)""",
                (cell_id, cell['channel_index'], cell['channel_name'], cell['mean_intensity'], cell['max_intensity']))
        # Update pipeline status
        cursor.execute("UPDATE pipeline_status SET feature_extraction = ? WHERE slide_id = ?",
                      (status, slide_id))
        conn.commit()
    except Exception as e:
        cursor.execute("UPDATE pipeline_status SET feature_extraction = ? WHERE slide_id = ?",
                      ('Failed', slide_id))
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Project folder name")
    parser.add_argument("--project", required=True, type=str, help="Enter the project folder name (case sensitive)")
    args = parser.parse_args()

    start_time = datetime.now()
    folder_name = args.project
    db_path = DB_PATH
    project_path = f"{ISILON_BASE}/{folder_name}"

    log_dir = os.path.join(project_path, 'logs')

    logger = setup_logging(folder_name, log_dir)
    
    logger.info("Scanning for files...")
    files = scan_for_files(f"{ISILON_BASE}/{folder_name}")
    logger.info(f"Found {len(files)} files")

    if SLURM_ARRAY:
        files = [files[SLURM_ARRAY]]

    for file in files:
        try:
            if is_already_processed(db_path, file, 'cell_features'):
                logger.info(f"Skipping {os.path.basename(file)}: already processed.")
                continue
            mask_dir = os.path.join(os.path.dirname(file), 'masks')
            file_name = os.path.splitext(os.path.basename(file))[0] + "_mask.tiff"
            mask_path = os.path.join(mask_dir, file_name)
            mask = tifffile.imread(f"{mask_path}")

            # Corrected illumination filename 
            corrected_dir = os.path.join(project_path, "corrected")
            corrected_illum = os.path.splitext(os.path.basename(file))[0]+ "_corrected.tiff"
            illum_path = os.path.join(corrected_dir, corrected_illum)
            
            logger.info(f"Extracting {os.path.basename(file)}...")
            write_morphology(db_path, file, extract_morphology(mask))
            write_intensity(db_path, file, extract_intensity(mask, illum_path))
        except Exception as e:
            logger.error(f"Slide {os.path.basename(file)} failed", exc_info=True)

    end_time = datetime.now() - start_time
    logger.info(f"Done! Finished in {end_time}")