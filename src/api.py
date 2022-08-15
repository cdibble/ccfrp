from ccfrp import Ccfrp
from thefuzz import fuzz, process
import pandas as pd
import logging
module_logger=logging.getLogger(__name__)


class Api(Ccfrp):
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
    def _join_location(self, df):
        return pd.merge(
            df,
            self.location,
            how = 'left',
            on = ['Area', 'Grid_Cell_ID']
        )
    def _join_species(self, df: pd.DataFrame):
        return pd.merge(
            df,
            self.species,
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
    #
    def get_df(self, type: str, common_name: str = None, monitoring_area: str = None, mpa_only: bool = False, **kwargs):
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
        fish_df = self._join_location(fish_df)
        fish_df = self._join_species(fish_df)
        return fish_df
    

if __name__=='__main__':
    import os
    os.chdir(os.path.dirname(__file__))
    api=Api()
    print(api.get_monitoring_area('Bodega'))
