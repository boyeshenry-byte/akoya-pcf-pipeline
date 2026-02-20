import os
import numpy as np
import tifffile
import sqlite3
from datetime import datetime
from skimage.filters import gaussian
from ingestion import scan_for_files

ISILON_BASE = os.environ.get("AKOYA_ISILON")
DB_PATH = os.environ.get("AKOYA_DB")

def compute_channel_stats(channel_array):
    """
    Compute signal statistics for a single channel. Returns a dict of stats.
    """

    res = {
        'shape': channel_array.shape,
        'min': channel_array.min(),
        'max': channel_array.max(),
        'mean': channel_array.mean(),
        'nonzero_fraction': np.count_nonzero(channel_array) / channel_array.size
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
            stats = compute_channel_stats(channel)
            flagged, message = flag_low_signals(stats)

            if not flagged:
                channel = correct_illumination(channel)

            res.append({
                'channel_index': i,
                'stats': stats,
                'flagged': flagged,
                'flag_message': message
            })

    return res

if __name__ == "__main__":
    folder_name = input("Enter project folder name: ")
    file_path = (f"{ISILON_BASE}/{folder_name}")
    db_path = DB_PATH
    
    print("Scanning for files...")
    files = scan_for_files(f"{ISILON_BASE}/{folder_name}")
    print(f"Found {len(files)} files")

    for file in files:
        print(f"Preprocessing {os.path.basename(file)}...")
        result = process_slide(file)
        for r in result:
            print(f"  Channel {r['channel_index']} — {r['flag_message']}")
        
    print("Done!")