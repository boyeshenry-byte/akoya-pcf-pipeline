import sqlite3
import os
import argparse
import shutil

DB_PATH = os.environ.get("AKOYA_DB")
ISILON_BASE = os.environ.get("AKOYA_ISILON")

parser = argparse.ArgumentParser(description="Project folder name")
parser.add_argument("--project", required=True, type=str, help="Enter the project folder name (case sensitive)")
args = parser.parse_args()

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("DELETE FROM cell_intensity")
cursor.execute("DELETE FROM cell_features;")
cursor.execute("DELETE FROM channel_stats;")
cursor.execute("DELETE FROM segmentation_results;")
cursor.execute("DELETE FROM pipeline_status;")
cursor.execute("DELETE FROM slides;")
cursor.execute("DELETE FROM runs;")

conn.commit()
conn.close()

folder_name = args.project
project_path = f"{ISILON_BASE}/{folder_name}"


if os.path.exists(f"{project_path}/anndata"):
    shutil.rmtree(f"{project_path}/anndata")
    print(f"{project_path}/anndata reset")
if os.path.exists(f"{project_path}/masks"):
    shutil.rmtree(f"{project_path}/masks")
    print(f"{project_path}/masks reset")
if os.path.exists(f"{project_path}/phenotyping"):
    shutil.rmtree(f"{project_path}/phenotyping")
    print(f"{project_path}/phenotyping reset")
if os.path.exists(f"{project_path}/qc_pngs"):
    shutil.rmtree(f"{project_path}/qc_pngs")
    print(f"{project_path}/qc_pngs reset")
if os.path.exists(f"{project_path}/spatial"):
    shutil.rmtree(f"{project_path}/spatial")
    print(f"{project_path}/spatial reset")

print(f"Reset complete for project: {folder_name}")