# =============================================================================
# preprocessing.py
# Author: Henry Boyes
# Institution: Cleveland Clinic
# Date: 2/20/2026
# Version: v0.3.0
# Contact: boyeshenry@gmail.com
# Description: This script computes the channel statistics for each channel of each slide.
# It flags channels that have low signals and corrects their illumination. It then writes the 
# channel statistics to the database and saves a composite PNG.
# =============================================================================

import os
import numpy as np
import tifffile
import sqlite3
import argparse
from datetime import datetime
from skimage.filters import gaussian
from skimage import exposure
from PIL import Image
from ingestion import scan_for_files
from utils import is_already_processed, setup_logging
import xml.etree.ElementTree as ET

ISILON_BASE = os.environ.get("AKOYA_ISILON")
DB_PATH = os.environ.get("AKOYA_DB")
SLURM_ARRAY = os.environ.get("SLURM_ARRAY_TASK_ID")
if SLURM_ARRAY:
    SLURM_ARRAY = int(SLURM_ARRAY)

parser = argparse.ArgumentParser(description="Project folder name")
parser.add_argument("--project", required=True, type=str, help="Enter the project folder name (case sensitive)")
args = parser.parse_args()

def compute_channel_stats(channel_array):
    """
    Compute signal statistics for a single channel. Returns a dict of stats.
    """

    res = {
        'shape': channel_array.shape,
        'min': float(channel_array.min()),
        'max': float(channel_array.max()),
        'mean': float(channel_array.mean()),
        'nonzero_fraction': float(np.count_nonzero(channel_array) / channel_array.size)
    }

    return res

def flag_low_signals(stats, threshold = 0.01):
    """
    Flag a channel if meaningful signal is below threshold. 

    threshold = minimum fraction of non-zero pixels expected.

    Returns (bool, str) - flagged for reason.
    """
    if stats['nonzero_fraction'] < threshold:
        return (True, "Low signal detected")

    return (False, "Signal OK")

def correct_illumination(channel_array):
    """
    Apply illumination correction to a single channel.
    Returns a corrected array.
    """
    background = gaussian(channel_array, sigma=50)
    # avoid division by zero
    corrected = channel_array/(background + 1e-6)
    
    return corrected

def process_slide(file_path):
    """
    Run preprocessing on all channels of a QPTIFF.
    Returns a list of dicts - one per channel.
    """
    
    res = []

    with tifffile.TiffFile(file_path) as tif:
        series = tif.series[0]
        for i, page in enumerate(series.pages):
            channel = page.asarray()
            meta = ET.fromstring(page.description)
            name = meta.find('Name')
            channel_name = name.text if name is not None else None
            stats = compute_channel_stats(channel)
            flagged, message = flag_low_signals(stats)

            if not flagged:
                channel = correct_illumination(channel)

            res.append({
                'channel_index': i,
                'channel_name': channel_name,
                'stats': stats,
                'flagged': flagged,
                'flag_message': message
            })

    return res

def write_preprocessing_results(db_path, file_path, results):
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
    any_flagged = any(r['flagged'] for r in results)

    try:
        for r in results:
            cursor.execute("""INSERT INTO channel_stats 
                (slide_id, channel_index, channel_name, min_intensity, max_intensity, 
                mean_intensity, nonzero_fraction, flagged, flag_message, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (slide_id, r['channel_index'], r['channel_name'],
                r['stats']['min'], r['stats']['max'],
                r['stats']['mean'], r['stats']['nonzero_fraction'],
                r['flagged'], r['flag_message'], datetime.now()))
        
        # Update pipeline status
        status = 'Failed' if any_flagged else 'Complete'
        cursor.execute("UPDATE pipeline_status SET preprocessing_qc = ? WHERE slide_id = ?",
                      (status, slide_id))
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()


def save_composite_png(file_path, output_dir):
    """
    Save a composite PNG of all channels for visual QC
    """

    os.makedirs(output_dir, exist_ok=True)

    with tifffile.TiffFile(file_path) as tif:
        series = tif.series[0]
        for i, page in enumerate(series.pages):
            channel = page.asarray()
            meta = ET.fromstring(page.description)
            name = meta.find('Name')
            channel_name = name.text if name is not None else None
            filename = channel_name if channel_name else f"channel_{i}"
            if channel.max()> 0:
                normalized = (channel/channel.max() * 255).astype(np.uint8)
            else:
                normalized = channel.astype(np.uint8)
            Image.fromarray(normalized).save(f"{output_dir}/{filename}.png")
    return

if __name__ == "__main__":
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
        if is_already_processed(db_path, file, "channel_stats"):
            logger.info(f"Skipping {os.path.basename(file)}: already processed.")
            continue
        logger.info(f"Preprocessing {os.path.basename(file)}...")
        result = process_slide(file)
        for r in result:
            logger.info(f"  Channel {r['channel_index']} — {r['flag_message']}")
        write_preprocessing_results(db_path, file, result)

        slide_name = os.path.splitext(os.path.basename(file))[0]
        output_dir = os.path.join(os.path.dirname(file), "qc_pngs", slide_name)
        save_composite_png(file, output_dir)
        logger.info(f" PNGs saved to {output_dir}")

    logger.info("Done!")