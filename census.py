from itertools import count
import os
import sqlite3

import pandas as pd
import plydata
import censusdata

DB = sqlite3.connect("geos.db")


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

    def build_geos(self, geo_names, geo_type="county"):
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

    def build_raw_dataframe(self, county_names, var_ids, src, year):
        """
        Queries census API for county-level data
            geos (list[list[str, str]]): List of state, county name pairs
            census_vars (list[dict]): List of variable specification dicts
            key (str): data.census.gov api key
        """

        # build list of var ids, and dict of id-name mappings

        states = set(state for state, _ in county_names)
        state_fips = [self.geoDB.get_state_fips(state) for state in states]

        all_state_data = pd.DataFrame()
        for state_ in state_fips:
            state_data = censusdata.download(
                src,
                year,
                censusdata.censusgeo([("state", state_), ("county", "*")]),
                var_ids,
                key=self.api_key,
            )

            all_state_data = all_state_data.append(state_data)

        # filtering to queried counties only
        all_county_data = (
            all_state_data.assign(county=all_state_data.index.map(lambda x: x.name))
            .set_index("county")
            .filter([f"{county}, {state}" for state, county in county_names], axis=0)
        )

        return all_county_data

    @staticmethod
    def apply_transforms(df, definitions):
        """
        df (Pandas.DataFrame): Dataframe containing raw data queried from Census
            API
        definitions (List[Tuple[str, str]]): List of (name, definition) pairs.
            Column definitions should be strings containing valid Python expressions
            to be evaluated in the context of the list of columns in df.

        returns (Pandas DataFrame): Dataframe containing transformed columns
        """

        all_vars = df.columns.values
        df = plydata.define(df, *definitions).drop(all_vars, axis=1)
        return df

    def build_formatted_dataframe(self, df, selected_vars):

        """
        Formats raw census data:
        - applies column definitions specified in vars_config
        - does various munging to get nicely formatted data

        df (Pandas.dataframe): dataframe containing raw data queried from Census
            API

        returns (Pandas.dataframe): well-formatted dataframe suitable for consumption
            by later view functions

        """

        column_definitions = [(var["name"], var["definition"]) for var in selected_vars]

        transformed_county_data = self.apply_transforms(df, column_definitions)

        vars_df = pd.DataFrame.from_dict(self.vars_config)[["category", "name"]]
        formatted_data = (
            transformed_county_data.transpose()
            .reset_index()
            .rename({"index": "name"}, axis=1)
            .merge(vars_df, on="name")
        )
        return formatted_data

    def build_dataframe(
        self, county_names, selected_vars, descriptions=False, src="acs5", year=2018
    ):
        """
        Creates dataframe view of variables in requested counties
        """

        all_vars = []
        for var in selected_vars:
            all_vars += var["vars"]
        raw_county_data = self.build_raw_dataframe(county_names, all_vars, src, year)
        formatted_county_data = self.build_formatted_dataframe(
            raw_county_data, selected_vars
        )
        if descriptions:
            pass

        return formatted_county_data

    def build_dict_view(self, df, categories):

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
        Builds view of census data stored in a dict that's easily consumed
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

        county_data = self.build_dataframe(county_names, selected_vars)

        county_data_dict = self.build_dict_view(
            county_data, set([var["category"] for var in selected_vars])
        )

        formatted_county_names = [
            "{county}, {state}".format(state=state, county=county)
            for state, county in county_names
        ]

        colnames = ["Column Name"] + formatted_county_names

        return county_data_dict, colnames

    def view_df(self, county_names, selected_var_ids):

        selected_vars = [
            var for var in self.vars_config if str(var["id"]) in selected_var_ids
        ]

        return self.build_dataframe(county_names, selected_vars)

    @property
    def available_vars(self):
        """
        Returns available variables. Partially constructs html for each option's
        tooltip.
        """

        var_list = []

        for category in self.available_categories:
            cat_list = [
                tuple(
                    [
                        {
                            "value": var["id"],
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

    @property
    def available_categories(self):
        return set([var["category"] for var in self.vars_config])