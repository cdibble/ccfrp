import sys
sys.path.append('../src/')
from angler import Angler
import pytest
import pandas as pd

@pytest.fixture(autouse=False)
def angler():
    angler = Angler()
    yield angler


def test_get_fish_type(angler):
    assert angler.get_fish_type('cab') == 'Cabezon'

def test_get_monitoring_area(angler):
    assert angler.get_monitoring_area('Bodega') == 'Bodega Head'

@pytest.mark.parametrize('params',['effort', 'length'])
def test_get_df(angler, params):
    df = angler.get_df(params)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert 'Phylum' in df.columns, "Failed to join species table properly"
    assert 'lon_center_point_dd' in df.columns, "Failed to join location table properly"
    start_time='2020-01-01'
    assert df.Date.min() <= pd.to_datetime(start_time)
    df = angler.get_df(params, start_time=start_time, common_name = 'Cabezon', monitoring_area='Bodega Head')
    assert df.Date.min() >= pd.to_datetime(start_time)
    assert len(df.Area.unique()) == 1