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
<<<<<<< HEAD
        race_data = formatted_data.get("Race")
        emp_data = formatted_data.get("Employment Status")
        sex_data = formatted_data.get("Sex by age")
        del sex_data[0]
        del race_data[0]
=======
        global data2
        data2 = censusViewer.view_df(selected_counties, selected_vars)
        # race_data = formatted_data["Race"]
        # emp_data = formatted_data["Employment Status"]
        # sex_data = formatted_data["Sex by age"]
        # del sex_data[0]
        # del race_data[0]
>>>>>>> d7ed48edff92f83fda47fd4e541dfa4d5c52ea05
        # print(race_data)

    rendered_table = render_output_table(categories, colnames, formatted_data)
    # print(formatted_data)

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


@server.route("/chart")
def render_chart():
    global data2
    form = StateForm(request.form)

    selected_counties = [
        [state.strip(), county]
        for county, state in [county.split(",") for county in form.geoSelector.data]
    ]

    selected_vars = [var for var in form.varSelector.data]

    print(data2)

    all_charts = {}

    for i in data2.columns:
        if i == 'name' or i == 'category':
            continue

        cat = data2[i].groupby(data2['category'])
        l_graph_dict = {}

        for c in cat:
            l_graph = []
            category = ""
            for index, row in enumerate(c):

                print("index: " + str(index))
                # print("content: " + str(type(row)))
                # print("content: " + str(row))
                if index == 0:
                    category = str(row)
                    print("category: " + str(row))
                else:
                    graph_dict = {}
                    for ii, v in row.items():
                        # print("i: " + str(i))
                        # print("name: " + str(data2.loc[i, 'name']))
                        # print("v: " + str(v))
                        graph_dict[str(data2.loc[ii, 'name'])] = v
                    l_graph.append(graph_dict)
            l_graph_dict[category] = l_graph
        all_charts[i] = l_graph_dict
    print(all_charts)

    return render_template(
        'chart.html',
        all_charts=all_charts,
    )


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
