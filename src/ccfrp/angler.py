from tokenize import group
from .ccfrp import Ccfrp
from thefuzz import fuzz, process
import pandas as pd
import shapely
import geopandas
import logging
module_logger=logging.getLogger(__name__)
from geojson import Polygon, FeatureCollection, dumps, Feature, Point
import geopandas
import shapely

class Angler(Ccfrp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    #
    def _time_filter(self, df, start_time=None, end_time=None, **kwargs):
        module_logger.info(f'filtering to start_time: {start_time}')
        if start_time:
            df = df.loc[df['Date'] >= pd.to_datetime(start_time)]
        if end_time:
            df = df.loc[df['Date'] < pd.to_datetime(end_time)]
        return df
    #
    def _fuzzy_get(self, match_str: str, match_choices: list, cutoff: float = 75):
        ops = process.extract(match_str, match_choices)
        ops = [x for x in ops if x[1] > cutoff]
        if len(ops) > 1:
            n = int(input(f"Select one (enter 0, 1, 2, ...): {ops}"))
            ops = ops[n]
        return ops[0][0]
    #
    def _join_location(self, df):
        '''
        Add the raw location information to the sample data
        '''
        return pd.merge(
            df,
            self.location[
                [x for x in self.location.columns if ((x not in df.columns) | (x in ['Area', 'Grid_Cell_ID']))]
                ],
            how = 'left',
            on = ['Area', 'Grid_Cell_ID']
        )
    def _join_species(self, df: pd.DataFrame):
        return pd.merge(
            df,
            self.species[
                [x for x in self.species.columns if ((x not in df.columns) | (x in ['Common_Name']))]
                ],
            how = 'left',
            on = ['Common_Name']
        )
    #
    def get_fish_type(self, common_name: str, **kwargs):
        '''
        common_name: str
            Best guess at common name. Will perform fuzzy match and get feedback if needed.
        '''
        fish_choices = self.species.Common_Name.unique()
        common_name = self._fuzzy_get(common_name, fish_choices)
        return common_name
    # 
    def get_monitoring_area(self, monitoring_area: str, **kwargs):
        '''
        monitoring_area: str
            Best guess at monitoring_area name. Will perform fuzzy match and get feedback if needed.
        '''
        areas = self.location.Area.unique()
        monitoring_area = self._fuzzy_get(monitoring_area, areas)
        return monitoring_area
    # get mean bounding points of each location
    def get_location_means(self):
        location_summary = self.location[['Area', 'MPA_Status', 'lat_1_dd', 'lon_1_dd', 'lat_2_dd','lon_2_dd', 'lat_3_dd', 'lon_3_dd', 'lat_4_dd', 'lon_4_dd']].groupby(['Area', 'MPA_Status']).mean().reset_index()
        return location_summary
    #
    def get_location_summary(self, df: pd.DataFrame = None, grouping_vars: list = ['Grid_Cell_ID', 'Area', 'MPA_Status'], **kwargs):
        '''
        Compute Polygons bounding each Area/MPA_Status/Grid_Cell_ID.
        Return a geodataframe with the geometry set to Polygons bounding each area.
        Can be used with self.location or any result of self.get_df() (since those have been joined with self.location)
        '''
        if df is None:
            print('using self.location')
            df = self.location
        raw_lat_lon_cols = ['lat_1_dd', 'lon_1_dd', 'lat_2_dd','lon_2_dd', 'lat_3_dd', 'lon_3_dd', 'lat_4_dd', 'lon_4_dd']
        df = df[~(
            df['lon_1_dd'].isna() |
            df['lon_2_dd'].isna() |
            df['lon_3_dd'].isna() |
            df['lon_4_dd'].isna() |
            df['lat_1_dd'].isna() |
            df['lat_2_dd'].isna() |
            df['lat_3_dd'].isna() |
            df['lat_4_dd'].isna()
        )]
        mdf = df[[*grouping_vars, *raw_lat_lon_cols]]
        # create a set, since there are many observations (one for each fish, not just one for each grid)
        mdf = mdf.groupby([*grouping_vars]).mean()
        mdf['poly'] = mdf.apply(lambda row: shapely.geometry.Polygon([
            (row.lon_1_dd, row.lat_1_dd),
            (row.lon_2_dd, row.lat_2_dd),
            (row.lon_3_dd, row.lat_3_dd),
            (row.lon_4_dd, row.lat_4_dd)
        ]), axis = 1)
        mdf = mdf.drop(columns = raw_lat_lon_cols).reset_index()
        mdf = geopandas.GeoDataFrame(mdf, geometry=mdf.poly).drop(columns='poly')
        # Now we are set to dissolve the Grid Cells.
        # But there are some bad geos that do not produce
            # valid Polygons. These need to be fixed via convex_hull
        mdf.loc[~mdf.geometry.apply(lambda x: x.is_valid), 'geometry'] = mdf.loc[~mdf.geometry.apply(lambda x: x.is_valid), 'geometry'].apply(lambda y: y.convex_hull)
        assert mdf.loc[~mdf.geometry.apply(lambda x: x.is_valid), 'geometry'].empty
        return mdf
    # get fish length or cpue dataframes
    def get_df(self, type: str, common_name: str = None, monitoring_area: str = None, mpa_only: bool = False, join_locations: bool = True, join_species: bool = True, **kwargs):
        if type == 'length':
            fish_df = self.length
        elif type == 'effort':
            fish_df = self.effort
        else:
            raise NotImplementedError(f"df type must be one of: ['length', 'effort']")
        if common_name:
            fish_df = fish_df.loc[fish_df['Common_Name'] == common_name]
        if monitoring_area:
            fish_df = fish_df.loc[fish_df['Area'] == monitoring_area]
        if mpa_only:
            fish_df = fish_df.loc[fish_df['MPA_Status'] == 'MPA']
        fish_df = self._time_filter(fish_df, **kwargs)
        if join_locations:
            fish_df = self._join_location(fish_df)
        if join_species:
            fish_df = self._join_species(fish_df)
        return fish_df
    # melt dataframe
    def melt_df(self, df, grouping_vars: list = ['Grid_Cell_ID', 'Area', 'MPA_Status'], **kwargs):
        '''
        Gets a melted dataframe of location info.
        Can be used with self.location or any result of self.get_df() (since those have been joined with self.location)
        '''
        mdf = df[[*grouping_vars, *['lat_1_dd', 'lon_1_dd', 'lat_2_dd','lon_2_dd', 'lat_3_dd', 'lon_3_dd', 'lat_4_dd', 'lon_4_dd']]].melt(
            id_vars = grouping_vars)
        mdf['point_no'] = mdf.variable.str[4]
        mdf = mdf.groupby([*grouping_vars, *['point_no', 'variable']]).mean().reset_index()
        lats = mdf.loc[mdf.variable.str.startswith('lat')]
        lons = mdf.loc[mdf.variable.str.startswith('lon')]
        df = pd.merge(lons, lats,on=[*grouping_vars, *['point_no']]).drop(columns=['variable_x', 'variable_y'])
        return df
    # 
    def make_location_polygons(self):
        '''
        Compute the extent of the polygons in a geojson type format.

        This is currently redundant with get_location_summary(). Haven't benchmarked to see which is faster, but they both produce valid geojson.
        '''
        df = self.location
        df = df[~(
            df['lon_1_dd'].isna() |
            df['lon_2_dd'].isna() |
            df['lon_3_dd'].isna() |
            df['lon_4_dd'].isna() |
            df['lat_1_dd'].isna() |
            df['lat_2_dd'].isna() |
            df['lat_3_dd'].isna() |
            df['lat_4_dd'].isna()
        )]
        df.loc[:, 'point_1'] = geopandas.points_from_xy(df['lon_1_dd'], df['lat_1_dd'])
        df.loc[:, 'point_2'] = geopandas.points_from_xy(df['lon_2_dd'], df['lat_2_dd'])
        df.loc[:, 'point_3'] = geopandas.points_from_xy(df['lon_3_dd'], df['lat_3_dd'])
        df.loc[:, 'point_4'] = geopandas.points_from_xy(df['lon_4_dd'], df['lat_4_dd'])
        df = df[['LTM_project_short_code', 'Monitoring_Group', 'Area',
        'MPA_names', 'CA_MPA_name_short', 'Grid_Cell_ID', 'Area_Code',
        'MPA_Status', 'point_1',
        'point_2', 'point_3', 'point_4']]
        df.loc[:, 'all_points'] = df[['point_1', 'point_2', 'point_3', 'point_4']].values.tolist()
        df.loc[:, 'poly'] = df['all_points'].apply(lambda x: shapely.geometry.Polygon([[point.x, point.y] for point in x]))
        gdf = geopandas.GeoDataFrame(df, geometry='poly')
        # sub_gdf = gdf[gdf.poly.apply(lambda x: x.is_valid)].dissolve(by=['Area', 'MPA_Status']).reset_index()
        # sub_gdf.loc[sub_gdf.Area == 'Anacapa Island'].total_bounds
        return gdf
    #
    def melt_df_area(self, df, grouping_vars: list = ['Grid_Cell_ID', 'Area', 'MPA_Status'], **kwargs):
        '''
        Gets a melted dataframe of location info.
        Can be used with self.location or any result of self.get_df() (since those have been joined with self.location)
        '''
        mdf = df[[
                *grouping_vars,
                *['lat_1_dd', 'lon_1_dd', 'lat_2_dd','lon_2_dd', 'lat_3_dd', 'lon_3_dd', 'lat_4_dd', 'lon_4_dd']
            ]].melt(
            id_vars = grouping_vars)
        min_lon = mdf.loc[mdf['variable'].str.startswith('lon')].groupby(['Area_MPA_Status']).apply(lambda g: g.min()).drop(columns=['Area_MPA_Status']).reset_index()
        max_lon = mdf.loc[mdf['variable'].str.startswith('lon')].groupby(['Area_MPA_Status']).apply(lambda g: g.max()).drop(columns=['Area_MPA_Status']).reset_index()
        min_lat = mdf.loc[mdf['variable'].str.startswith('lat')].groupby(['Area_MPA_Status']).apply(lambda g: g.min()).drop(columns=['Area_MPA_Status']).reset_index()
        max_lat = mdf.loc[mdf['variable'].str.startswith('lat')].groupby(['Area_MPA_Status']).apply(lambda g: g.max()).drop(columns=['Area_MPA_Status']).reset_index()
        lons = pd.concat([min_lon, max_lon])
        lats = pd.concat([min_lat, max_lat])
        df = pd.merge(lons, lats, on = ['Area_MPA_Status']).drop(columns=['variable_x', 'variable_y']).sort_values(['value_y', 'value_x'], ascending=[False, False]) #.groupby(['Area_MPA_Status']).mean().reset_index()
        return df
    #
    def fish_length_map_prep(
        self,
        df: pd.DataFrame = None,
        common_name: str = None,
        start_time:str = None,
        end_time: str = None,
        id_column: str = 'Grid_Cell_ID',
        feat_properties: list = ['Area', 'MPA_Status'],
        **kwargs
        ):
        '''
        Aggregate fish data to the appropriate spatial scale basd on `id_column`
            and create a geospatial FeatureCollection with specified `feat_properties` that specify the 
            geometries that match the aggregated fish data.
        
        Outputs can be used for Chloropleth/Raster plots.

        Returns
        ---------
        DataFrame, FeatureCollection
            The DataFrame with aggregated fish data and properties.
            The FeatureCollection with geojson specifying geometries for fish data aggregations.
        '''
        if df is None:
            df = self.get_df(
                'length',
                common_name=common_name,
                start_time=start_time,
                end_time=end_time,
                )
        print('getting location summary polygons')
        locs = self.get_location_summary(df, grouping_vars=[id_column])
        grouping_cols = list(set([id_column, *feat_properties]))
        print(f"Grouping by {grouping_cols}")
        df = df[[*grouping_cols, 'Length_cm']].groupby(grouping_cols).mean().reset_index()
        gdf = pd.merge(
            df,
            locs,
            how = 'left',
            on = id_column
        )
        geo = self._create_features(gdf, id_column=id_column, feat_properties=feat_properties, **kwargs)
        return df, geo

    @staticmethod
    def _create_features(df: pd.DataFrame, id_column: str, feat_properties: list = ['Area', 'MPA_Status'], **kwargs):
        features=[]
        for grid_cell in df[id_column].unique():
            sub_df = df.loc[df[id_column] == grid_cell]
            assert sub_df.shape[0]==1
            properties={x: sub_df[x].unique()[0] for x in feat_properties}
            feat_i = Feature(
                id = grid_cell,
                geometry = sub_df.geometry.iloc[0],
                properties=properties
                )
            features.append(feat_i)
        return FeatureCollection(features)

if __name__=='__main__':
    import os
    os.chdir(os.path.dirname(__file__))
    angler=Angler()
    print(angler.get_monitoring_area('Bodega'))
