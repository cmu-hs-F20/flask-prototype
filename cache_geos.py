import json

import censusdata
from tqdm import tqdm


def build_states_cache(cache_path):
    
    print('Building states cache\n')
    states = censusdata.geographies(censusdata.censusgeo([('state', '*')]), 'acs5', 2018)
    states_dict = {key: state.params()[0][1] for key, state in states.items()}
    states_json = json.dumps(states_dict, indent=4)

    counties_dict = dict()
    
    for state_name, state in tqdm(states.items(), desc='Building counties cache'):
        counties = censusdata.geographies(censusdata.censusgeo([state.geo[0], ('county', '*')]), 'acs5', 2018)
        
        state_counties = {}
        for key, county in counties.items():
            county_name = key.split(',')[:-1][0]
            state_counties[county_name] = county.geo[1][1]
        counties_dict[state_name] = state_counties

    counties_json = json.dumps(counties_dict, indent=4)

    with open(cache_path, 'w') as f:
        f.write('states = ' + states_json + '\n')
        f.write('counties = ' + counties_json)

if __name__ == '__main__':
    build_states_cache('states.py')
