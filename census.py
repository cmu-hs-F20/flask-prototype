from itertools import product
import os
import sqlite3
from functools import reduce

from multiprocessing import Pool
import pandas as pd
import plydata
import censusdata

DB = sqlite3.connect("geos.db")
N_PROCESSES = 4


class GeoDB:
    def __init__(self, db_path):

        if os.path.isfile(db_path):
            self.db = sqlite3.connect(db_path, check_same_thread=False)
        else:
            raise Exception(
                f"""Database {db_path} not found. Try running cache_geos.py to populate database."""
            )

    def get_states(self):
        """
        returns:
            list[str]: List of state names
        """
        cur = self.db.cursor()
        cur.execute(
            """
            SELECT state 
            FROM states; 
        """
        )

        states = [state[0] for state in cur.fetchall()]
        cur.close()
        return states

    def get_all_counties(self):

        cur = self.db.cursor()
        cur.execute("select state from states order by state")
        states = [state[0] for state in cur.fetchall()]

        stateslist = []
        for state in states:
            cur.execute(
                """
                    select county || ', ' || state 
                    from counties 
                    join states using (state)
                    where state = "{state}"
                    order by county
                """.format(
                    state=state
                )
            )

            counties = cur.fetchall()

            counties_tuple = tuple((county[0], county[0]) for county in counties)

            stateslist.append(tuple([state, counties_tuple]))

        return tuple(stateslist)

    def get_state_counties(self, state):
        """
        Gets counties in state

        arguments:
            state (str): state name
        returns:
            list[str]: List of county names
        """

        cur = self.db.cursor()
        cur.execute(
            f"""
            select county 
            from counties 
            where state == "{state}"
        """
        )

        counties = [county[0] for county in cur.fetchall()]
        cur.close()

        return counties

    def get_state_fips(self, state_name):
        """
        Gets fips code for state

        arguments:
            state_name (str): name of state
        returns:
            str: fips code of state
        """

        cur = self.db.cursor()
        cur.execute(
            """
            SELECT state_fips
            FROM states
            WHERE state == ? 
        """,
            (state_name,),
        )

        state_fips = cur.fetchall()[0][0]

        return state_fips

    def get_county_fips(self, state_name, county_name):
        """
        Gets fips code for county in state

        arguments:
            state_name (str): name of state
            county_name (str): name of county
        returns:
            str: fips code of county
        """
        cur = self.db.cursor()
        cur.execute(
            """
            SELECT county_fips
            FROM counties
            WHERE state == ? AND county == ?
        """,
            (state_name, county_name),
        )
        county_fips = cur.fetchall()[0][0]

        return county_fips


class CensusViewer:
    def __init__(self, geoDB, vars_config, api_key):
        self.geoDB = geoDB
        self._vars_config = vars_config
        self.api_key = api_key

    @property
    def vars_config(self):
        return [dict(var, id=i) for i, var in enumerate(self._vars_config)]
    
    @property
    def available_categories(self):
        return sorted(list(set([var["category"] for var in self.vars_config])))

    def _build_geos(self, geo_names, geo_type="county"):
        '''
        Builds list of state, county fips code pairs to pass to census api
        args:
            geo_names (List[Tuple[str, str]]): List of state, county name pairs
            geo_type: Geography type
        returns:
            List[List[str, str]]
        '''
        
        if geo_type != "county":
            raise NotImplementedError

        # build list of state-county fips code pairs
        geo_fips = []
        for state, county in geo_names:
            geo_fips.append(
                [
                    self.geoDB.get_state_fips(state),
                    self.geoDB.get_county_fips(state, county),
                ]
            )
        return geo_fips

    @staticmethod
    def _build_state_dataframe(state_fips, var_ids, src, year, tabletype, api_key):
        """
        Queries census API for county-level data
            geos (list[list[str, str]]): List of state, county name pairs
            census_vars (list[dict]): List of variable specification dicts
            key (str): data.census.gov api key
        """

        # build list of var ids, and dict of id-name mappings

        state_data = censusdata.download(
            src,
            year,
            censusdata.censusgeo([("state", state_fips), ("county", "*")]),
            var_ids,
            key=api_key,
            tabletype=tabletype,
        )

        # we'll need this
        #     all_state_data = all_state_data.append(state_data)

        return state_fips, state_data

    @staticmethod
    def _apply_transforms(df, definitions):
        """
        df (Pandas.DataFrame): Dataframe containing raw data queried from Census
            API
        definitions (List[Tuple[str, str]]): List of (name, definition) pairs.
            Column definitions should be strings containing valid Python expressions. 
            Expressions can reference other columns in df by name. Example:

            [
                (
                    "Column Name",
                    "(B02001_001E - B02001_002E) / B02001_001E"
                )
            ]

            This expression references columns containing data for census variables
            B02001_001E (population, all races) and B02001_002E (population, white).

            It calculates the proportion of a geography's population identifying as 
            a race other than White.

            See https://plydata.readthedocs.io/en/latest/generated/plydata.one_table_verbs.define.html
            for more on how these expressions are evaluated 

        returns (Pandas DataFrame): Dataframe containing transformed columns
        """

        all_vars = df.columns.values
        df = plydata.define(df, *definitions).drop(all_vars, axis=1)
        return df

    def _build_formatted_dataframe(self, df, selected_vars):

        """
        Formats raw census data:
        - applies column definitions specified in vars_config
        - does various munging to get nicely formatted data

        df (Pandas.dataframe): dataframe containing raw data queried from Census
            API
        selected_vars (List[Dict]): List of variables (vars_config filtered based 
            on user selection) 

        returns (Pandas.dataframe): well-formatted dataframe suitable for consumption
            by later view functions

        """

        column_definitions = [(var["name"], var["definition"]) for var in selected_vars]

        transformed_county_data = self._apply_transforms(df, column_definitions)

        vars_df = pd.DataFrame.from_dict(self.vars_config)[["category", "name"]]
        formatted_data = (
            transformed_county_data.transpose()
            .reset_index()
            .rename({"index": "name"}, axis=1)
            .merge(vars_df, on="name")
        )
        return formatted_data

    def _build_dataframe(
        self, county_names, selected_vars, descriptions=False, src="acs5", year=2018
    ):
        """
        Creates dataframe view of variables in requested counties. Main helper 
        view function, ie does most of the work of munging frontend queries and 
        coordinating lower-level helper functions.

        Does some optimization to run census api queries in parallel. Consider tweaking 
        N_PROCESSES parameter to affect performance.

        args:
            county_names (List[str]): List of state, county name pairs
            selected_vars (List[Dict]): List of variable dicts
            descriptions (boolean): Boolean controlling whether to include variable
                descriptions in df output (not implemented)
            src (str): Census api source parameter
            year (int): Census api year parameter        
        """

        # generate list of selected census api variable ids

        all_vars = []
        for var in selected_vars:
            all_vars += var["vars"]

        tabletypes = [
            ("B", r"detail"),
            ("S", r"subject"),
            ("DP", r"profile"),
            ("CP", r"cprofile"),
        ]

        all_vars = []
        for var in selected_vars:
            all_vars += var["vars"]

        # Within one census api query, all vars must be from same table type &
        # all counties must be from same state. So we make one call to 
        # censusdata.download for each state x tabletype.  

        # So:
        # 1. build list of states

        states = set(state for state, _ in county_names)
        state_fips = [self.geoDB.get_state_fips(state) for state in states]

        # 2. build list of tabletypes (& corresponding vars)

        tabletype_jobs = []
        for table_prefix, tabletype in tabletypes:

            tabletype_vars = [var for var in all_vars if var.startswith(table_prefix)]

            if tabletype_vars:
                tabletype_jobs.append([tabletype_vars, tabletype])

        # 3. cross product: states x tabletypes

        census_jobs = []

        for state_fips, (tabletype_vars, tabletype) in product(
            state_fips, tabletype_jobs
        ):
            census_jobs.append(
                [state_fips, tabletype_vars, src, year, tabletype, self.api_key]
            )

        # 4. run all of the downloads (in parallel)

        pool = Pool(N_PROCESSES)

        raw_dfs = pool.starmap(self._build_state_dataframe, census_jobs)

        # 5. merge all

        merged_state_dfs = []
        for state in set(state for state, _ in raw_dfs):
            raw_state_dfs = [
                state_data for state_, state_data in raw_dfs if state_ == state
            ]
            merged_state_df = reduce(
                lambda x, y: pd.merge(
                    x, y, left_index=True, right_index=True, how="outer"
                ),
                raw_state_dfs,
            )

            merged_state_dfs.append(merged_state_df)

        merged_dfs = pd.concat(
            merged_state_dfs,
        )

        # 6. filter on counties

        raw_data = (
            merged_dfs.assign(county=merged_dfs.index.map(lambda x: x.name))
            .set_index("county")
            .filter([f"{county}, {state}" for state, county in county_names], axis=0)
        )

        # 7. format (apply column definitions)

        formatted_county_data = self._build_formatted_dataframe(raw_data, selected_vars)

        if descriptions:
            pass

        return formatted_county_data

    def _build_dict_view(self, df, categories):
        '''
        Converts df view to dict.
        
        args:
            df (Pandas.dataframe): dataframe output of queried data
            categories (List[str]): List of category names
        '''

        formatted_data_dict = dict()
        for category in categories:
            rows = df.loc[df.category == category].drop("category", axis=1).values
            if rows.ndim == 1:
                rows = [rows.tolist()]
            else:
                rows = rows.tolist()
            formatted_data_dict[category] = rows
        return formatted_data_dict

    def view_dict(self, county_names, selected_var_ids, src="acs5", year=2018):

        """
        Builds view of census data stored in a dict that's consumed
        by Flask renderer.

        Args:
            county_names (list[list(str, str)]): List of county, state name pairs
            src (str): data.census.gov API source to be used. (currently unused)
            year (int): Year to query census data. (currently unused)

        returns (dict, list[str]):
        -   dict containing census output formatted to be consumed by renderer.
            schema:
                {
                    'category_name':[
                        [col1_data, col2_data, ...],
                        ...
                    ],
                }
        -   List of column names
        """

        selected_vars = [
            var for var in self.vars_config if str(var["id"]) in selected_var_ids
        ]

        county_data = self._build_dataframe(county_names, selected_vars)

        county_data_dict = self._build_dict_view(
            county_data, sorted(list(set([var["category"] for var in selected_vars])))
        )

        formatted_county_names = [
            "{county}, {state}".format(state=state, county=county)
            for state, county in county_names
        ]

        colnames = ["Column Name"] + formatted_county_names

        return county_data_dict, colnames

    def view_df(self, county_names, selected_var_ids):

        """
        Builds view of census data stored in a Pandas dataframe

        Args:
            county_names (list[list(str, str)]): List of county, state name pairs
            src (str): data.census.gov API source to be used. (currently unused)
            year (int): Year to query census data. (currently unused)

        returns Pandas.DataFrame
        """

        selected_vars = [
            var for var in self.vars_config if str(var["id"]) in selected_var_ids
        ]

        return self._build_dataframe(county_names, selected_vars)

    @property
    def available_vars(self):
        """
        Returns available variables. Partially constructs html for each option's
        tooltip.
        """

        var_list = []

        #TODO: Refactor tooltip HTML insertion to view level. Current approach is... kinda hacky

        for category in self.available_categories:
            cat_list = [
                tuple(
                    [
                        {
                            "value": var["id"],
                            # adds tooltip to be rendered by bootstrap-select multiselect component
                            "data-content": '<a data-toggle="tooltip" title="{}">{}</a>'.format(
                                var.get("description", ""), var["name"]
                            ),
                        },
                        var["name"],
                    ]
                )
                for var in self.vars_config
                if var["category"] == category
            ]
            var_list.append(tuple([category, tuple(cat_list)]))
        return var_list
