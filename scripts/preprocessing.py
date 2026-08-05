# =============================================================================
# preprocessing.py
# Author: Henry Boyes
# Institution: Cleveland Clinic
# Date: 2/20/2026
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
from skimage.transform import downscale_local_mean
from PIL import Image
from ingestion import scan_for_files
from utils import is_already_processed, setup_logging
import xml.etree.ElementTree as ET

ISILON_BASE = os.environ.get("AKOYA_ISILON")
DB_PATH = os.environ.get("AKOYA_DB")
SLURM_ARRAY = os.environ.get("SLURM_ARRAY_TASK_ID")
if SLURM_ARRAY:
    SLURM_ARRAY = int(SLURM_ARRAY)


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

def select_sigma(channel_array, logger):
    """
    This function downscales the cell images to compute Guassian sigma for illumination gradient correction. 

    : args : 
    
    channel_array : np array
        An np array of channel illumination values

    : returns :
        
    sigma : float    
        A float value of the corrected Gaussian sigma for illumination correction
    """

    # Downsample and scale sigma
    K = channel_array.shape[0]//8000
    logger.info(f"K = {K}")

    downsample = downscale_local_mean(channel_array, (K,K))

    sigma_candidates = [10, 20, 50, 75, 100, 150]
    stds = []
    # Compute stds
    for candidate in sigma_candidates:
        scaled_candidate = max(1,candidate//K)
        corrected = correct_illumination(downsample, scaled_candidate)
        stds.append(corrected.std())
    
    # Create curve of stds. Select point of diminishing returns
    stds_array = np.array(stds)
    diffs = np.diff(stds_array) # First diff
    best_idx = np.argmin(diffs)

    coarse_sigma = sigma_candidates[best_idx]
    lower = max(sigma_candidates[best_idx-1] if best_idx > 0 else coarse_sigma//2, K+1)
    upper = sigma_candidates[best_idx+1] if best_idx < len(sigma_candidates)-1 else coarse_sigma*2
    fine_candidates = sorted(set(np.linspace(lower, upper, 10).astype(int).tolist()))

    logger.info(f"Coarse stds: {list(zip(sigma_candidates, stds))}")
    logger.info(f"Coarse sigma: {coarse_sigma}, Fine candidates: {fine_candidates}")

    scaled_fine_vals = [max(1, c//K) for c in fine_candidates]

    if len(set(scaled_fine_vals)) <3:
        logger.info(f"Fine tunning skipped: Insufficient distinct values. Returning coarse sigma {coarse_sigma}")
        return coarse_sigma

    fine_stds = []
    # Compute fine stds
    for candidate in fine_candidates:
        scaled_fine = max(1,candidate//K)
        fine_corrected = correct_illumination(downsample, scaled_fine)
        fine_stds.append(fine_corrected.std())
    
    # Create curve of stds. Select point of diminishing returns
    fine_stds_array = np.array(fine_stds)
    fine_diffs = np.diff(fine_stds_array) # First diff
    fine_best_idx = np.argmin(fine_diffs) 

    logger.info(f"Fine stds: {list(zip(fine_candidates, fine_stds))}")
    logger.info(f"Selected sigma: {fine_candidates[fine_best_idx]}")

    return fine_candidates[fine_best_idx]

def correct_illumination(channel_array, sigma):
    """
    Apply illumination correction to a single channel.
    Returns a corrected array.
    """
    background = gaussian(channel_array, sigma=sigma)
    # avoid division by zero
    corrected = channel_array/(background + 1e-6)
    
    return corrected

def process_slide(file_path, logger, sigma=None):
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
            sigma = args.sigma if args.sigma is not None else select_sigma(channel, logger)
            logger.info(f" Channel {channel_name}: sigma={sigma}")

            if not flagged:
                channel = correct_illumination(channel, sigma)

            res.append({
                'channel_index': i,
                'channel_name': channel_name,
                'stats': stats,
                'flagged': flagged,
                'flag_message': message,
                'corrected_array': channel,
                'sigma': sigma
            })

    return res

def save_corrected_tiff(file_path, results, output_dir):
    """
    This function save the corrected channels for use downstream. 
    """

    # Stack corrections
    corrected = np.stack([r['corrected_array'] for r in results]).astype(np.float32)

    # Save channel names
    channel_names = [r['channel_name'] for r in results]

    file_name = os.path.splitext(os.path.basename(file_path))[0] + "_corrected.tiff"
    output_path = os.path.join(output_dir, file_name)
    tifffile.imwrite(output_path, corrected, compression='zstd', bigtiff = True, metadata={'axes': 'CYX', 'Channel':{'Name': channel_names}})

    return

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
        conn.rollback()
        raise
    finally:
        conn.close()


def save_composite_png(results, output_dir):
    """
    Save a composite PNG of all channels for visual QC
    """

    os.makedirs(output_dir, exist_ok=True)

    for i, r in enumerate(results):
        channel = r['corrected_array']
        channel_name= r['channel_name']
        filename = channel_name if channel_name else f"channel_{i}"
        if channel.max() > 0:
            p_low = np.percentile(channel, 1)
            p_high = np.percentile(channel, 99)
            normalized = np.clip((channel - p_low) / (p_high - p_low + 1e-6) * 255, 0, 255).astype(np.uint8)
        else:
            normalized = channel.astype(np.uint8)
        Image.fromarray(normalized).save(f"{output_dir}/{filename}.png")

    return

if __name__ == "__main__":
    # Set folder and sigma
    parser = argparse.ArgumentParser(description="Project folder name")
    parser.add_argument("--project", required=True, type=str, help="Enter the project folder name (case sensitive)")
    parser.add_argument("--sigma", default=None, type=float, help="Guassian sigma for illumination correction. If not specified,\
        sigma is automatically selected per slide via CV minimization.")
    args = parser.parse_args()

    start_time=  datetime.now()
    folder_name = args.project
    db_path = DB_PATH
    project_path = f"{ISILON_BASE}/{folder_name}"

    # Make dir for corrected .tiff files
    corrected_dir = os.path.join(project_path, 'corrected')
    os.makedirs(corrected_dir, exist_ok=True)

    log_dir = os.path.join(project_path, 'logs')

    logger = setup_logging(folder_name, log_dir)
    
    logger.info("Scanning for files...")
    files = scan_for_files(f"{ISILON_BASE}/{folder_name}")
    logger.info(f"Found {len(files)} files")

    if SLURM_ARRAY:
        files = [files[SLURM_ARRAY]]

    for file in files:
        try:
            if is_already_processed(db_path, file, "channel_stats"):
                logger.info(f"Skipping {os.path.basename(file)}: already processed.")
                continue
            logger.info(f"Preprocessing {os.path.basename(file)}...")
            result = process_slide(file, logger, args.sigma)
            for r in result:
                logger.info(f"  Channel {r['channel_index']} — {r['flag_message']}")
            write_preprocessing_results(db_path, file, result)
            save_corrected_tiff(file, result, corrected_dir)

            slide_name = os.path.splitext(os.path.basename(file))[0]
            output_dir = os.path.join(os.path.dirname(file), "qc_pngs", slide_name)
            save_composite_png(result, output_dir)
            logger.info(f" PNGs saved to {output_dir}")
        except Exception as e:
            logger.error(f"Slide {os.path.basename(file)} failed", exc_info=True)

    end_time = datetime.now() - start_time
    logger.info(f"Done! Finished in {end_time}")