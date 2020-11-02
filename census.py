import json
import sqlite3

import pandas as pd
import censusdata

from states import states, counties

DB = sqlite3.connect('geos.db')
    
def get_pop(state_name):
    try: 
        state = get_state_fips(state_name)
    except:
        return 'No state found'
    
    geo = censusdata.censusgeo((('state', state),))

    pop = censusdata.download('acs5', 2018, geo, ['B01001_001E'])

    return pop['B01001_001E'][0]

def get_data(geos, census_vars, key):

    geo_fips = []
    for state, county in geos:
        geo_fips.append([get_state_fips(state), get_county_fips(state, county)])


    unique_states = {state for state, _ in geo_fips}

    all_state_data = pd.DataFrame()
    for state in unique_states:
        tmp_data = censusdata.download(
            'acs5',
            2018,
            censusdata.censusgeo([('state', state), ('county', '*')]),
            census_vars,
            key=key
        )

        all_state_data = all_state_data.append(tmp_data)

    all_state_data = (
        all_state_data.assign(county = all_state_data.index.map(lambda x: x.name))
            .set_index('county')
            .filter([f'{county}, {state}' for state, county in geos], axis = 0)
            .reset_index()
    )

    return all_state_data



def get_data_old(geo_names, census_vars, key):
    '''
    geo_names: fips
    census_vars: list(str) containing desired census variables
    ('042', '003')
    '''


    county_data: pd.DataFrame = pd.DataFrame()
    geos = []

    geo_fips = []
    for state, county in geo_names:
        geo_fips.append([get_state_fips(state), get_county_fips(state, county)])

    for state in set(state for state, _ in geo_names):
        
        state_fips = get_state_fips(state)

        state_data = censusdata.download(
                'acs5',
                2018,
                censusdata.censusgeo([('state', state_fips), ('county', '*')]),
                census_vars,
                key=key
            )
        
        county_data.append(state_data)
                  
    for i in range(len(geo_names)):
        
        state_name, county_name = geo_names[i]
        state_fips, county_fips = geo_fips[i]

        geo = censusdata.censusgeo([('state', state_fips), ('county', county_fips)])

        temp_df = state_data.loc[geo]
        temp_df.assign(County = f'{county_name}, {state_name}')
               
        geo_dict = censusdata.geographies(censusdata.censusgeo([('state', state_fips), ('county', county_fips)]), 'acs5', 2018)
        for value in geo_dict.values():
            geos.append(value)


        if geos: 
            state_data = state_data.filter(geos, axis=0)
            breakpoint()

        county_data = county_data.append(state_data)
    
    
    
    return county_data.reset_index()    

class GeoDB:

    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)

    def get_states(self):
        
        cur = self.db.cursor()
        cur.execute('''
            SELECT state 
            FROM states; 
        ''')
        
        states = [state[0] for state in cur.fetchall()] 
        cur.close()
        return states

    def get_counties(self, state):
        print(f'{state}')
        cur = self.db.cursor()
        cur.execute(f'''
            select county 
            from counties 
            where state == "{state}"
        ''')

        counties = [county[0] for county in cur.fetchall()]
        cur.close()

        return counties

def get_state_fips(state_name):

    stateFips = states[state_name]

    return stateFips

def get_county_fips(state_name, county_name):

    countyFips = counties[state_name][county_name]

    return countyFips

if __name__ == '__main__':
    db = GeoDB('geos.db')
    print(db.get_states())
    print(db.get_counties('New York'))