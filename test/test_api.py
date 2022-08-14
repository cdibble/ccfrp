import sys
sys.path.append('../src/')
from api import Api
import pytest
import pandas as pd

@pytest.fixture(autouse=False)
def api():
    api = Api()
    yield api


def test_get_fish_type(api):
    assert api.get_fish_type('cab') == 'Cabezon'

def test_get_monitoring_area(api):
    assert api.get_monitoring_area('Bodega') == 'Bodega Head'

@pytest.mark.parametrize('params',['effort', 'length'])
def test_get_df(api, params):
    df = api.get_df(params)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert 'Phylum' in df.columns, "Failed to join species table properly"
    assert 'lon_center_point_dd' in df.columns, "Failed to join location table properly"
    start_time='2020-01-01'
    assert df.Date.min() <= pd.to_datetime(start_time)
    df = api.get_df(params, start_time=start_time, common_name = 'Cabezon', monitoring_area='Bodega Head')
    assert df.Date.min() >= pd.to_datetime(start_time)
    assert len(df.Area.unique()) == 1