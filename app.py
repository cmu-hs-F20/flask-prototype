from flask import (
    Flask,
    render_template,
    request,
    session,
    Markup,
    json,
    make_response,
    Blueprint,
)
from wtforms import Form, TextField, validators
from wtforms_components.fields import SelectMultipleField
from census import CensusViewer, GeoDB

import pandas as pd
import dash_table
import dash

import secrets

import chartkick

ck = Blueprint(
    "ck_page", __name__, static_folder=chartkick.js(), static_url_path="/static"
)


server = Flask(__name__)
server.secret_key = secrets.app_secret

server.register_blueprint(ck, url_prefix="/ck")
server.jinja_env.add_extension("chartkick.ext.charts")

with open("vars.json", "r") as f:
    vars_config = json.loads(f.read())

geoDB = GeoDB("geos.db")
censusViewer = CensusViewer(
    geoDB=geoDB, vars_config=vars_config, api_key=secrets.census_key
)

DataFrame = pd.read_csv("iris.csv")

app = dash.Dash(__name__, server=server, routes_pathname_prefix="/dash/")

app.layout = dash_table.DataTable(
    id="table",
    data=DataFrame.to_dict("records"),
    columns=[{"id": c, "name": c} for c in DataFrame.columns],
    page_action="none",
    style_table={"height": "300px", "overflowY": "auto"},
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
            "data-actions-box": "true",
            "data-selected-text-format": "count > 2",
        },
    )


@server.route("/", methods=["GET", "POST"])
def dashboard():
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
        race_data = {}
        emp_data = {}
        sex_data = {}
    else:
        formatted_data, colnames = censusViewer.view_dict(
            county_names=selected_counties, selected_var_ids=selected_vars
        )
        categories = list(formatted_data.keys())
        race_data = formatted_data["Race"]
        emp_data = formatted_data["Employment Status"]
        sex_data = formatted_data["Sex by age"]
        del sex_data[0]
        del race_data[0]
        # print(race_data)

    rendered_table = render_output_table(categories, colnames, formatted_data)

    # race_data = render_race(selected_counties)

    print(form.errors)

    return render_template(
        "state.html",
        form=form,
        rendered_table=rendered_table,
        data_available=True if selected_counties else False,
        race_data=race_data,
        emp_data=emp_data,
        sex_data=sex_data,
    )


# def render_race(selected_counties):
#     formatted_data, colnames = censusViewer.view(county_names=selected_counties)
#     print(formatted_data)
#     return formatted_data


@server.route("/download-data", methods=["POST"])
def return_download():

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


# @server.route("/chart")
# def return_chart():
#
#     # data = censusViewer.build_dataframe()
#
#     return render_template("state.html", data=data)


def render_output_table(categories, column_names, rows):
    rendered = render_template(
        "census_table.html",
        categories=categories,
        column_names=column_names,
        rows=rows,
        zip=zip,
    )

    return Markup(rendered)


if __name__ == "__main__":
    server.run(debug=True)
