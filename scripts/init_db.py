# =============================================================================
# init_db.py
# Author: Henry Boyes
# Institution: Cleveland Clinic
# Date: 2/25/2026
# Contact: boyeshenry@gmail.com
# Description: This script creates the database for Akoya PCF projects.
# =============================================================================

import sqlite3
import os

DB_PATH = os.environ.get("AKOYA_DB")
file = os.path.join(os.path.dirname(__file__), '..', 'schema.sql')

with open(file, "r") as f:
    schema = f.read()

conn = sqlite3.connect(DB_PATH)
conn.executescript("DROP TABLE IF EXISTS channel_stats; DROP TABLE IF EXISTS pipeline_status; \
    DROP TABLE IF EXISTS segmentation_results; DROP TABLE IF EXISTS slides; DROP TABLE IF EXISTS runs; ")
conn.executescript(schema)
conn.commit()
conn.close()
print("Database created")