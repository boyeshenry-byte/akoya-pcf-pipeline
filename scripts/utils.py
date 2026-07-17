# =============================================================================
# utils.py
# Author: Henry Boyes
# Institution: Cleveland Clinic
# Date: 2/25/2026
# Contact: boyeshenry@gmail.com
# Description: This script contains the shared pipeline utilities including database helpers and logging setup.
# =============================================================================

import sqlite3
import logging
import os


def is_already_processed(db_path, file_path, table):
    """
    Check if a slide has already been processed in segmentation.
    Returns True if already processed.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT slide_id FROM slides WHERE file_path = ?", (file_path,))
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        return False
    
    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE slide_id = ?", (row[0],))
    result = cursor.fetchone()[0] > 0
    conn.close()
    return result


def setup_logging(project, log_dir):
    logger = logging.getLogger("akoya_pcf")
    logger.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # File handler
    file_handler = logging.FileHandler(os.path.join(log_dir, f"{project}_pipeline.log"))
    file_handler.setFormatter(formatter)

    # Stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # Add to logger
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger