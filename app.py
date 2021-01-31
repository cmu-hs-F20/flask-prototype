from flask import (
    Flask,
    render_template,
    request,
    Markup,
    json,
    make_response,
    Blueprint,
)
from wtforms import Form, validators
from title_select import SelectMultipleField
from census import CensusViewer, GeoDB
from load_config import load_config

import secrets

import chartkick

ck = Blueprint(
    "ck_page", __name__, static_folder=chartkick.js(), static_url_path="/static"
)

server = Flask(__name__)
server.secret_key = secrets.app_secret

server.register_blueprint(ck, url_prefix="/ck")
server.jinja_env.add_extension("chartkick.ext.charts")


geoDB = GeoDB("geos.db")
censusViewer = CensusViewer(
    geoDB=geoDB, vars_config=load_config("vars.json"), api_key=secrets.census_key
)


class StateForm(Form):
    geoSelector = SelectMultipleField(
        "Select Counties:",
        validators=[validators.DataRequired()],
        choices=geoDB.get_all_counties(),
        render_kw={
            "class": "selectpicker",
            "multiple": "true",
            "data-live-search": "true",
            "data-actions-box": "true",
            "data-multiple-separator": " | ",
            "data-selected-text-format": "count > 4",
            "data-size": "10",
            "data-done-button": "true",
        },
    )

    varSelector = SelectMultipleField(
        "Select Variables to Display:",
        validators=[validators.DataRequired()],
        choices=censusViewer.available_vars,
        render_kw={
            "class": "selectpicker",
            "multiple": "true",
            "data-live-search": "true",
            "data-actions-box": "true",
            "data-selected-text-format": "count > 2",
        },
    )


data2 = None


@server.route("/", methods=["GET", "POST"])
def dashboard():
    '''
    Main dashboard view. Includes forms for selecting geographies (counties) and 
    variables to display.
    '''
    form = StateForm(request.form)

    selected_counties = [
        [state.strip(), county]
        for county, state in [county.split(",") for county in form.geoSelector.data]
    ]

    selected_vars = [var for var in form.varSelector.data]

    if not selected_counties:
        categories = [""]
        colnames = ["No column data!"]
        formatted_data = {"": [["No row data!"]]}
        # race_data = {}
        # emp_data = {}
        # sex_data = {}
    else:
        formatted_data, colnames = censusViewer.view_dict(
            county_names=selected_counties, selected_var_ids=selected_vars
        )
        categories = list(formatted_data.keys())
        global data2
        data2 = censusViewer.view_df(selected_counties, selected_vars)
        # race_data = formatted_data["Race"]
        # emp_data = formatted_data["Employment Status"]
        # sex_data = formatted_data["Sex by age"]
        # del sex_data[0]
        # del race_data[0]
    rendered_table = render_output_table(categories, colnames, formatted_data)

    print(form.errors)

    return render_template(
        "state.html",
        form=form,
        rendered_table=rendered_table,
        data_available=True if selected_counties else False,
        # race_data=race_data,
        # emp_data=emp_data,
        # sex_data=sex_data,
    )


def render_output_table(categories, column_names, rows):
    '''
    Helper function that renders selected data in HTML.

    Args:
        categories (List[str]): List of category names
        column_names (List[str]): List of column names (usually county names)
        rows (Dict[str: List[List[str]]]): Dict with one key/value pair
            for each category. Example:

                {"Sex": [
                    [['Population: Female', 28326.0, 106919.0, 24411.0], 
                    ['Population: Male', 26874.0, 101188.0, 24200.0]]
                ]}
            
            Data in this format is produced by CensusViewer.view_dict()
    '''
    rendered = render_template(
        "census_table.html",
        categories=categories,
        column_names=column_names,
        rows=rows,
        zip=zip,
        enum=enumerate,
    )

    return Markup(rendered)


@server.route("/download-data", methods=["POST"])
def return_download():
    '''
    Endpoint for downloading csv containing selected data
    '''
    form = StateForm(request.form)

    selected_counties = [
        [state.strip(), county]
        for county, state in [county.split(",") for county in form.geoSelector.data]
    ]

    selected_vars = [var for var in form.varSelector.data]

    data = censusViewer.view_df(selected_counties, selected_vars)
    response = make_response(data.to_csv(index=False))
    response.headers["Content-Disposition"] = "attachment; filename=county_acs_data.csv"
    response.headers["Content-Type"] = "text/csv"

    return response


@server.route("/chart", methods=["POST"])
def render_chart():
    global data2
    form = StateForm(request.form)

    selected_counties = [
        [state.strip(), county]
        for county, state in [county.split(",") for county in form.geoSelector.data]
    ]

    selected_vars = [var for var in form.varSelector.data]

    all_charts = {}

    for i in data2.columns:
        if i == "name" or i == "category":
            continue

        cat = data2[i].groupby(data2["category"])
        l_graph_dict = {}

        for c in cat:
            l_graph = []
            category = ""
            for index, row in enumerate(c):

                if index == 0:
                    category = str(row)
                else:
                    graph_dict = {}
                    for ii, v in row.items():
                        graph_dict[str(data2.loc[ii, "name"])] = v
                    l_graph.append(graph_dict)
            l_graph_dict[category] = l_graph
        all_charts[i] = l_graph_dict

    return render_template(
        "chart.html",
        all_charts=all_charts,
    )




if __name__ == "__main__":
    server.run(debug=True)
