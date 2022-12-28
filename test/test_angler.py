import sys
sys.path.append('../src/')
from ccfrp.angler import Angler
import pytest
import pandas as pd
import geopandas as gpd

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

# Test location
def test_get_location_means(angler):
    locs = angler.get_location_means()
    assert isinstance(locs, pd.DataFrame)
    assert not locs.empty
    assert all(
        [x in locs.columns for x in ['Area', 'MPA_Status', 'lat_1_dd', 'lon_1_dd', 'lat_2_dd', 'lon_2_dd', 'lat_3_dd', 'lon_3_dd', 'lat_4_dd', 'lon_4_dd']]
    )

def test_get_location_summary(angler):
    locs = angler.get_location_summary()
    assert isinstance(locs, gpd.GeoDataFrame)
    assert not locs.empty
    assert all(
        [x in locs.columns for x in ['Grid_Cell_ID', 'Area', 'MPA_Status', 'geometry']]
    )
    for area in locs.Area:
        if area == 'South Cape Mendocino':
            # not sure why this one has two Area/MPA_Status/Grid_Cell_IDs with the same geometry
            continue
        area_locs = locs.loc[locs.Area == area]
        assert len(area_locs.geometry.unique()) == len(area_locs.Grid_Cell_ID.unique())

def test_make_location_polygons(angler):
    locs = angler.make_location_polygons()
    assert isinstance(locs, gpd.GeoDataFrame)
    assert not locs.empty
    assert all(
        [x in locs.columns for x in ['LTM_project_short_code', 'Monitoring_Group', 'Area', 'MPA_names',
       'CA_MPA_name_short', 'Grid_Cell_ID', 'Area_Code', 'MPA_Status',
       'point_1', 'point_2', 'point_3', 'point_4', 'all_points', 'poly']]
    )
    for area in locs.Area:
        if area == 'South Cape Mendocino':
            # not sure why this one has two Area/MPA_Status/Grid_Cell_IDs with the same geometry
            continue
        area_locs = locs.loc[locs.Area == area]
        assert len(area_locs.geometry.unique()) == len(area_locs.Grid_Cell_ID.unique())