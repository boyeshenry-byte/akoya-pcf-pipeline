import pandas as pd
import anndata
import pytest
import sys
sys.path.insert(0, 'scripts')
from anndata_export import build_anndata

def test_build_anndata():
    # Create synthetic data
    features = pd.DataFrame({
        'cell_id': [1, 2],
        'area': [100, 200],
        'centroid_x': [14.5, 54.5],
        'centroid_y': [14.5, 54.5],
        'eccentricity': [0.0, 0.1],
        'perimeter': [38.0, 40.0],
        'solidity': [1.0, 0.9]
    })

    mean_intensity = pd.DataFrame({
        'DAPI': [100.0, 200.0],
        'Opal 480': [50.0, 75.0]
    }, index=pd.Index([1, 2], name='cell_id'))

    max_intensity = pd.DataFrame({
        'DAPI': [150.0, 250.0],
        'Opal 480': [75.0, 100.0]
    }, index=pd.Index([1, 2], name='cell_id'))

    channel_meta = pd.DataFrame({
        'channel_name': ['DAPI', 'Opal 480'],
        'channel_index': [0, 1]
    })

    res = build_anndata(features, mean_intensity, max_intensity, channel_meta, 1, 'name')

    assert res.X.shape == (2, 2)  # 2 cells, 2 channels
    assert 'max_intensity' in res.layers
    assert 'spatial' in res.obsm
    assert res.obsm['spatial'].shape == (2, 2)  # 2 cells, x and y coords