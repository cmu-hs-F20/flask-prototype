from flask import Flask, render_template, request, session, Markup, json, make_response
from wtforms import Form, TextField, validators
from wtforms_components.fields import SelectMultipleField
from census import CensusViewer, GeoDB

import pandas as pd
import dash_table
import dash

import secrets

server = Flask(__name__)
server.secret_key = secrets.app_secret

with open("new_vars_schema_example.json", "r") as f:
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
        for county, state in [
            county.split(",") for county in request.form.getlist("geoSelector")
        ]
    ]

    if not selected_counties:
        categories = [""]
        colnames = ["No column data!"]
        formatted_data = {"": [["No row data!"]]}
    else:
        formatted_data, colnames = censusViewer.view(county_names=selected_counties)
        categories = list(formatted_data.keys())

    rendered_table = render_output_table(categories, colnames, formatted_data)

    print(form.errors)

    return render_template(
        "state.html",
        form=form,
        rendered_table=rendered_table,
        data_available=True if selected_counties else False,
    )


@server.route("/download-data")
def return_download():

    data = censusViewer.build_dataframe(
        [[geo["state_name"], geo["county_name"]] for id, geo in session["geos"].items()]
    )
    response = make_response(data.to_csv(index=False))
    response.headers["Content-Disposition"] = "attachment; filename=county_acs_data.csv"
    response.headers["Content-Type"] = "text/csv"

    return response


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
