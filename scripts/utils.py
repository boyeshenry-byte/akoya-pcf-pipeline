# =============================================================================
# utils.py
# Author: Henry Boyes
# Institution: Cleveland Clinic
# Date: 2/25/2026
# Version: v0.1.0
# Contact: boyeshenry@gmail.com
# Description: This script contains the shared pipeline utilities.
# =============================================================================

import sqlite3

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