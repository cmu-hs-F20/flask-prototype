import json

import pandas as pd
import censusdata

from states import states, counties

    
def get_pop(state_name):
    try: 
        state = get_state_fips(state_name)
    except:
        return 'No state found'
    
    geo = censusdata.censusgeo((('state', state),))

    pop = censusdata.download('acs5', 2018, geo, ['B01001_001E'])

    return pop['B01001_001E'][0]

def get_data(geo_names, census_vars, key):
    '''
    geo_names: fips
    '''
    county_data: pd.DataFrame = pd.DataFrame()
    geos = None
    # geos: List[censusdata.censusgeo] = [censusdata.geographies(censusdata.censusgeo([('state', state), ('county', county)]), 'acs5', 2018) for state, county in geo_names]

    for state in set(state for state, county in geo_names):
        state_data = censusdata.download(
                'acs5',
                2018,
                censusdata.censusgeo([('state', state), ('county', '*')]),
                census_vars,
                key=key
            )

        if geos: 
            state_data = state_data.filter(geos, axis=0)

        county_data = county_data.append(state_data).reset_index()

    return county_data

def get_state_fips(state_name):

    stateFips = states[state_name]

    return stateFips