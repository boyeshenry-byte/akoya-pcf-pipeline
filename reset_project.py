import sqlite3
import os
import argparse
import shutil

DB_PATH = os.environ.get("AKOYA_DB")
ISILON_BASE = os.environ.get("AKOYA_ISILON")

parser = argparse.ArgumentParser(description="Project folder name")
parser.add_argument("--project", required=True, type=str, help="Enter the project folder name (case sensitive)")
args = parser.parse_args()


def reset_db(folder_name, cursor):
    project_filter = f"%{folder_name}%"

    cursor.execute("""DELETE FROM cell_intensity WHERE cell_id IN (
                        SELECT cell_id FROM cell_features WHERE slide_id IN (
                            SELECT slide_id FROM slides WHERE file_path LIKE ?));""", (project_filter,))
    cursor.execute("""DELETE FROM cell_features WHERE slide_id IN (
                        SELECT slide_id FROM slides WHERE file_path LIKE ?);""", (project_filter,))
    cursor.execute("""DELETE FROM channel_stats WHERE slide_id IN(
                        SELECT slide_id FROM slides WHERE file_path LIKE ?);""", (project_filter,))
    cursor.execute("""DELETE FROM segmentation_results WHERE slide_id IN (
                        SELECT slide_id FROM slides WHERE file_path LIKE ?);""", (project_filter,))
    cursor.execute("""DELETE FROM pipeline_status WHERE slide_id IN (
                        SELECT slide_id FROM slides WHERE file_path LIKE ?);""", (project_filter,))
    cursor.execute("DELETE FROM slides WHERE file_path LIKE ?;", (project_filter,))




def reset_dir (project_path):
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

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    folder_name = args.project
    project_path = f"{ISILON_BASE}/{folder_name}"

    try:
        reset_db(folder_name, cursor)
        conn.commit()
        conn.close()
        print("Database reset")
        reset_dir(project_path)
        print("Directory reset")
    except Exception as e:
        print(e)

    print(f"{folder_name} reset complete")