import numpy as np
import pytest
import sys
import logging
sys.path.insert(0, 'scripts')
from feature_extraction import extract_morphology

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