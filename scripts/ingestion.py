import os
import tifffile
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

ISILON_BASE = os.environ.get("AKOYA_ISILON")
DB_PATH = os.environ.get("AKOYA_DB")


def scan_for_files(base_path):
    """
    Scan base_path for QPTIFF files and returns a list of file paths
    """
    file_path = []

    # Ensure file exists

    if not os.path.exists(base_path):
        print('Folder not found!')
        return []

    # Find .qptiff files in the folder

    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith(".qptiff"):
                full_path = os.path.join(root, file)
                file_path.append(full_path)
    return file_path

def extract_metadata(file_path):
    """
    Extract metadata from a QPTIFF file. Returns a dict.
    """

    with tifffile.TiffFile(file_path) as tif:
        t_series = tif.series[0]
        meta = ET.fromstring(tif.pages[0].description)
        slide = meta.find("SlideID").text

        markers = []
        for page in tif.series[0].pages:
            meta = ET.fromstring(page.description)
            names = meta.find('Name')
            if names is not None:
                markers.append(names.text)
            
    meta_dict = {
        'file_path': file_path,
        'file_name': os.path.basename(file_path),
        'slide_id': slide,
        'num_channels': t_series.shape[0],
        'markers': markers,
        'image_shape': t_series.shape[1:]
    }

    return meta_dict   

def validate_file(metadata):
    """
    Check metadata for completeness. Returns (bool, str) - valid message.
    """
    if not metadata['file_path']:
        return (False, "Missing file path")
    
    elif not metadata["file_name"]:
        return (False, "Missing file name")

    elif not metadata["slide_id"]:
        return (False, "Missing slide ID")
    
    elif not metadata['num_channels']:
        return (False, "Missing number of channels")
    
    elif not metadata['markers']:
        return (False, "Missing marker names")

    elif metadata['num_channels'] != len(metadata['markers']):
        return (False, "Number of channels does not match number of markers")

    elif not metadata['image_shape']:
        return (False, "Missing image dimensions")
    
    return (True, "All checks passed!")
    

def write_to_db(db_path, metadata):
    """
    Write a validated file record to the Database.
    """

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM slides WHERE file_path = ?", (metadata['file_path'],))
    count = cursor.fetchone()[0]

    if count == 0:
        try:
            cursor.execute("insert into slides (slide_name, file_path, file_name, num_channels) values (?, ?, ?, ?)",
            (metadata['slide_id'], metadata['file_path'], metadata['file_name'], metadata['num_channels']))
            slide_id = cursor.lastrowid
            cursor.execute("""INSERT INTO pipeline_status (slide_id, ingestion, preprocessing_qc, segmentation, feature_extraction, phenotyping, spatial_analysis) 
            VALUES (?, ?, ?, ?, ?, ?, ?)""", 
            (slide_id, 'Not Started', 'Not Started', 'Not Started', 'Not Started', 'Not Started', 'Not Started'))
            conn.commit()
        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()
        finally:
            conn.close()
    else:
        print(f"Skipping {metadata['file_name']}: Already in DataBase")
        conn.close()
        return
    
if __name__ == "__main__":
    folder_name = input("Enter project folder name: ")
    db_path = DB_PATH
    
    print("Scanning for files...")
    files = scan_for_files(f"{ISILON_BASE}/{folder_name}")
    print(f"Found {len(files)} files")

    for file in files:
        print(f"Processing {os.path.basename(file)}...")
        metadata = extract_metadata(file)
        valid, message = validate_file(metadata)
        if valid:
            write_to_db(db_path, metadata)
        else:
            print(f"Skipping {os.path.basename(file)}: {message}")

    print("Done!")