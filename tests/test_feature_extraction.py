import numpy as np
import pytest
import sys
import logging
import tifffile
sys.path.insert(0, 'scripts')
from feature_extraction import extract_morphology, extract_intensity

def test_extract_morphology():
    mask = np.zeros((100, 100), dtype=np.int32)
    mask[10:20, 10:20] = 1  # cell 1 — a 10x10 square
    mask[50:60, 50:60] = 2  # cell 2 — another 10x10 square

    res = extract_morphology(mask)
    res_sorted = sorted(res, key=lambda x: x['centroid_x'])

    assert res_sorted[0]['area'] == 100
    assert 35 <= res_sorted[0]['perimeter'] <= 45
    assert res_sorted[0]['centroid_x'] == pytest.approx(14.5)
    assert res_sorted[0]['centroid_y'] == pytest.approx(14.5)
    assert res_sorted[0]['eccentricity'] < 0.5
    assert res_sorted[0]['solidity'] == 1.0

    assert res_sorted[1]['area'] == 100
    assert 35 <= res_sorted[1]['perimeter'] <= 45
    assert res_sorted[1]['centroid_x'] == pytest.approx(54.5)
    assert res_sorted[1]['centroid_y'] == pytest.approx(54.5)
    assert res_sorted[1]['eccentricity'] < 0.5
    assert res_sorted[1]['solidity'] == 1.0

def create_test_tiff(tmp_path):
    # Create a small 2-channel tiff with known values
    data = np.zeros((2, 100, 100), dtype=np.float32)
    data[0, 10:20, 10:20] = 100.0  # channel 0 signal in cell region
    data[1, 10:20, 10:20] = 200.0  # channel 1 signal in cell region
    
    path = tmp_path / "test.tiff"
    tifffile.imwrite(str(path), data, 
                     metadata={'axes': 'CYX', 
                               'Channel': {'Name': ['DAPI', 'Opal 480']}})
    return path

def get_result(data, channel, label):
    return next(r for r in data if r['channel_name'] == channel and r['label'] == label)

    results = extract_intensity(mask, str(test_path), logger)

    cell1_dapi = get_result(results, 'DAPI', 1)
    cell1_opal = get_result(results, 'Opal 480', 1)

    assert cell1_dapi['mean_intensity'] == pytest.approx(100.0)
    assert cell1_opal['mean_intensity'] == pytest.approx(200.0)