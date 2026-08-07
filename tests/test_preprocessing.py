import numpy as np
import pytest
import sys
import logging
sys.path.insert(0, 'scripts')
from preprocessing import compute_channel_stats, flag_low_signals, select_sigma, correct_illumination

def test_compute_channel_stats():
    test_array = np.array([0, 1, 2, 3, 4])
    res = compute_channel_stats(test_array)
    assert res['min'] == 0
    assert res['max'] ==4
    assert res['mean'] == 2.0
    assert res['nonzero_fraction'] == 0.8

def test_compute_channel_stats_blank_array():
    test_array = np.zeros(5)
    res = compute_channel_stats(test_array)
    assert res['min'] == 0
    assert res['max'] ==0
    assert res['mean'] == 0
    assert res['nonzero_fraction'] == 0

def test_flag_low_signals():
    threshold_low = {'nonzero_fraction': 0.001}
    threshold_high = {'nonzero_fraction':0.02}
    low = flag_low_signals(threshold_low)
    high = flag_low_signals(threshold_high)

    assert low == (True, "Low signal detected")
    assert high == (False, "Signal OK")

def test_flag_low_signals_boundary():
    boundary_stats = {'nonzero_fraction': 0.01}
    flagged, message = flag_low_signals(boundary_stats)
    assert flagged == False
    assert message == "Signal OK"

def test_select_sigma():
    logger = logging.getLogger('test')
    test_array = np.random.randint(0, 1000, (16000, 16000), dtype=np.uint16)
    sigma_candidates = [10, 20, 50, 75, 100, 150]
    res = select_sigma(test_array, logger)

    assert res >= sigma_candidates[0]
    assert res <=sigma_candidates[-1]*2

def test_select_sigma_blank_array():
    logger = logging.getLogger('test')
    test_array = np.zeros((16000, 16000), dtype=np.uint16)
    res = select_sigma(test_array, logger)

    # blank arrays return sigma=5 due to fine candidate lower bound
    assert res == 5

def test_select_sigma_with_gradient():
    logger = logging.getLogger('test')
    # Create array with broad illumination gradient
    x = np.linspace(0, 1, 16000)
    y = np.linspace(0, 1, 16000)
    xx, yy = np.meshgrid(x, y)
    gradient = (np.exp(-((xx-0.5)**2 + (yy-0.5)**2) / 0.1) * 1000).astype(np.uint16)
    result = select_sigma(gradient, logger)
    # A broad gradient should require a large sigma
    assert result >= 50

def test_correct_illumination():
    x = np.linspace(0, 255, 100)
    y = np.linspace(0, 255, 100)
    xx, yy = np.meshgrid(x, y)
    test_array = (xx + yy).astype(np.float32)
    corrected = correct_illumination(test_array, sigma=10)
    assert corrected.std() < test_array.std()