import json
import os
import sqlite3

import pandas as pd
import censusdata

from states import states, counties

DB = sqlite3.connect('geos.db')


class GeoDB:

    def __init__(self, db_path):
        if os.path.isfile(db_path):  
            self.db = sqlite3.connect(db_path, check_same_thread=False)
        else:
            raise Exception(f'''Database {db_path} not found. Try running cache_geos.py to populate database.''')
    def get_states(self):
        '''
        returns:
            list[str]: List of state names
        '''
        cur = self.db.cursor()
        cur.execute('''
            SELECT state 
            FROM states; 
        ''')
        
        states = [state[0] for state in cur.fetchall()] 
        cur.close()
        return states

    def get_counties(self, state):
        '''
        Gets counties in state
        
        arguments:
            state (str): state name
        returns:
            list[str]: List of county names
        '''

        cur = self.db.cursor()
        cur.execute(f'''
            select county 
            from counties 
            where state == "{state}"
        ''')

        counties = [county[0] for county in cur.fetchall()]
        cur.close()

        return counties

    def get_state_fips(self, state_name):
        '''
        Gets fips code for state

        arguments:
            state_name (str): name of state
        returns:
            str: fips code of state
        '''

        cur = self.db.cursor()
        cur.execute('''
            SELECT state_fips
            FROM states
            WHERE state == ? 
        ''', (state_name,))
        
        state_fips = cur.fetchall()[0][0]

        return state_fips

    def get_county_fips(self, state_name, county_name):
        '''
        Gets fips code for county in state

        arguments:
            state_name (str): name of state
            county_name (str): name of county
        returns:
            str: fips code of county
        '''
        cur = self.db.cursor()
        cur.execute('''
            SELECT county_fips
            FROM counties
            WHERE state == ? AND county == ?
        ''', (state_name, county_name))
        county_fips = cur.fetchall()[0][0]
        
        return county_fips


def get_data(geos, census_vars, key):

    '''
    Gets and formats census data:
    1. Loads data for each county from each state
    2. Filters to requested counties only
    3. Formats: nice row and column names
    4. Returns dataframe w/ results

    geos (list[list[str, str]]): List of state, county name pairs
    census_vars (list[dict]): List of variable specification dicts
    key (str): data.census.gov api key
    '''

    # build list of var ids, and dict of id-name mappings
    var_ids = [var['id'] for var in census_vars]
    var_name_mappings = {var['id']: var['name'] for var in census_vars}

    # build list of state-county fips code pairs
    geoDB = GeoDB('geos.db')
    geo_fips = []
    for state, county in geos:
        geo_fips.append([geoDB.get_state_fips(state), geoDB.get_county_fips(state, county)])

    # get data for all counties in each unique state
    unique_states = {state for state, _ in geo_fips}

    all_state_data = pd.DataFrame()
    for state in unique_states:
        tmp_data = censusdata.download(
            'acs5',
            2018,
            censusdata.censusgeo([('state', state), ('county', '*')]),
            var_ids,
            key=key
        )

        all_state_data = all_state_data.append(tmp_data)

    # final munging step
    all_state_data = (
        all_state_data.assign(county = all_state_data.index.map(lambda x: x.name))
            .set_index('county')
            .filter([f'{county}, {state}' for state, county in geos], axis = 0)
            .rename(columns = var_name_mappings)
            .reset_index()
    )

    return all_state_data


if __name__ == '__main__':
    db = GeoDB('geos.db')
    print(db.get_states())
    print(db.get_counties('New York'))
    print(db.get_state_fips('Pennsylvania'))
    print(db.get_county_fips('Pennsylvania', 'Bedford County'))