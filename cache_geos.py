import sqlite3

import censusdata
from tqdm import tqdm


def build_states_cache(db_name):
    
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.executescript('''
        DROP TABLE IF EXISTS STATES;
        DROP TABLE IF EXISTS COUNTIES;
        CREATE TABLE STATES (state text, state_fips text);
        CREATE TABLE COUNTIES (state text, county text, county_fips text);
    ''')

    states = censusdata.geographies(censusdata.censusgeo([('state', '*')]), 'acs5', 2018)

    for state, state_geo in states.items():
        state_fips = state_geo.params()[0][1]

        c.execute(f'''
            INSERT INTO states VALUES ('{state}', '{state_fips}')
        ''')

    for state_name, state_geo in tqdm(states.items(), desc='Building counties cache'):
        counties = censusdata.geographies(censusdata.censusgeo([state_geo.geo[0], ('county', '*')]), 'acs5', 2018)

        for county, county_geo in counties.items():
            # extracting county name from string formatted as "county, state"
            county_name = county.split(',')[:-1][0] 
            county_fips = county_geo.geo[1][1]
            
            if 'Brien' in county:
                print(county)
                print(county_name)
            
            c.execute(
                'INSERT INTO counties VALUES (?, ?, ?)', 
                (state_name, county_name, county_fips)
            )

    conn.commit()

if __name__ == '__main__':
    build_states_cache('geos.db')
