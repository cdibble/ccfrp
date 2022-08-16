import pandas as pd
import os


class Ccfrp:
    def __init__(self, db_path: str = '../db', raw: bool = False):
        self.db_path = db_path
        self.tables = ['effort', 'length', 'location', 'species']
        if not raw:
            self.get_local_data()
        else:
            self.get_raw_data()
    # datetime helper
    def _set_datetimes(self, df, date_var: str = 'Date'):
        df[date_var] = pd.to_datetime(df[date_var])
        return df
    # read raw database
    def get_raw_data(self):
        '''
        Raw data is from: https://search.dataone.org/view/doi%3A10.25494%2FP6901R
        And also documented (with older data) here: https://data.ca.gov/dataset/california-collaborative-fisheries-research-program
        '''
        self.effort = self._set_datetimes(pd.read_csv('https://cn.dataone.org/cn/v2/resolve/urn%3Auuid%3A077b4f1a-c8cb-47b4-a693-91ecf9bb026a'))
        self.length = self._set_datetimes(pd.read_csv('https://cn.dataone.org/cn/v2/resolve/urn%3Auuid%3A870dc9c1-44b5-41bb-861e-106f104f19a0'))
        self.location = pd.read_csv('https://cn.dataone.org/cn/v2/resolve/urn%3Auuid%3A6e056607-dc15-421e-bce1-d1502b22ceaa')
        self.species = pd.read_csv('https://cn.dataone.org/cn/v2/resolve/urn%3Auuid%3A3b70fbd7-c446-494e-8b76-d033ef1685b7', encoding_errors='ignore')
    # read local database
    def get_local_data(self):
        self.effort = self._set_datetimes(pd.read_csv(os.path.join(self.db_path, 'effort.csv')))
        self.length = self._set_datetimes(pd.read_csv(os.path.join(self.db_path, 'length.csv')))
        self.location = pd.read_csv(os.path.join(self.db_path, 'location.csv'))
        self.species = pd.read_csv(os.path.join(self.db_path, 'species.csv'))
    # write local databse
    def write_local_db(self, endpoint):
        assert endpoint in ['all', *self.tables],f"{endpoint} is an invalid endpoint to write. must be either 'all' or one of {self.tables}"
        if endpoint == 'all':
            endpoint = self.tables
        elif not isinstance(endpoint, list):
            endpoint = list(endpoint)
        for df in endpoint:
            df = getattr(self, endpoint)
            df.to_csv(os.path.join(self.db_path, f'{endpoint}.csv'))
