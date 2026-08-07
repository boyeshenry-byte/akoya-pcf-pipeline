import numpy as np
import pytest
import sys
import logging
import sqlite3
sys.path.insert(0, 'scripts')
from ingestion import scan_for_files, write_to_db

def test_scan_for_files(tmp_path):
    # create fake .qptiff files
    (tmp_path / "slide1.qptiff").touch()
    (tmp_path / "slide2.qptiff").touch()
    (tmp_path / "not_a_slide.txt").touch() # Should not be found

    res = scan_for_files(str(tmp_path))
    assert len(res) == 2

def test_write_to_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Initialize schema
    with open('schema.sql', 'r') as f:
        conn.executescript(f.read())
    
    fake_metadata = {
        'file_path': '/fake/path/slide1.qptiff',
        'file_name': 'slide1.qptiff',
        'slide_id': 'TEST001',
        'num_channels': 8,
        'markers': ['DAPI', 'Opal 480', 'Opal 520'],
        'image_shape': (40000, 30000)
    }
    
    write_to_db(cursor, fake_metadata, run_id=None)
    conn.commit()
    
    # Verify it was written
    row = cursor.execute("SELECT * FROM slides WHERE file_name = ?", ('slide1.qptiff',)).fetchone()
    assert row is not None
    
    conn.close()