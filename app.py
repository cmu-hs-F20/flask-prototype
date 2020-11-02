from flask import Flask, render_template, request, session, Markup, json, make_response
from wtforms import Form, TextField, validators
from flask_debugtoolbar import DebugToolbarExtension
from census import get_data, GeoDB

import pandas as pd
import dash_table
import dash

import secrets

server = Flask(__name__)
server.secret_key = secrets.app_secret

geoDB = GeoDB('geos.db')

with open('vars.json', 'r') as f:
    CENSUS_VARS = json.loads(f.read())

DataFrame = pd.read_csv('iris.csv')

app = dash.Dash(
    __name__,
    server=server,
    routes_pathname_prefix='/dash/')


app.layout = dash_table.DataTable(
    id="table",
    data=DataFrame.to_dict('records'),
    columns=[{'id': c, 'name': c} for c in DataFrame.columns],
    page_action='none',
    style_table={'height': '300px', 'overflowY': 'auto'}
)


class StateForm(Form):
    state = TextField(
        'State:', 
        validators = [validators.DataRequired()],
        render_kw = {
            'class': 'geo_input',
            'autocomplete_list': json.dumps(geoDB.get_states()),
        }
    )

    county = TextField(
        'County:', 
        validators = [validators.DataRequired()], 
        render_kw= {
            'class': 'geo_input',
            'disabled':'true',
            'autocomplete_list': json.dumps([''])
        }
    )


    @server.route('/', methods = ['GET', 'POST'])
    def dashboard():
        form = StateForm(request.form)

        if 'geos' not in session:
            session['geos'] = {}
            colnames = ['No column data!']
            row_data = ['No row data!']
        else:
            print(session['geos'])
            data = get_data(
                [[geo['state_name'], geo['county_name']] for id, geo in session['geos'].items()],
                CENSUS_VARS,
                secrets.census_key,
            )
  
            colnames = data.columns.values
            row_data = list(data.values.tolist())

        print(form.errors)

        selected_states = []
        for id, geo in session['geos'].items():
            selected_states.append(render_selected_geo(
                geo['state_name'],
                geo['county_name'],
                id
            ))

        return render_template(
            'state.html', 
            form=form,
            selected_states=selected_states,
            column_names = colnames,
            row_data = row_data,
            zip=zip
        )

    @server.route('/register-geo', methods = ['POST'])
    def register_geo():

        saved_geos = session.get('geos')

        form = StateForm(request.form)
        state_name = form.state.data
        county_name = form.county.data

        # breakpoint()

        if state_name not in geoDB.get_states():
            return f"No such state: {state_name}", 500

        if county_name not in geoDB.get_counties(state_name):
            return f"No such county {county_name} in state {state_name}", 500
       
        saved_geos[request.form['id']] = {
            'state_name': state_name,
            'county_name': county_name,
        }
        session['geos'] = saved_geos

        return render_selected_geo(state_name, county_name, request.form['id'])


    @server.route('/drop-geo', methods = ['POST'])
    def dropGeo():

        saved_geos = session.get('geos')
        try:
            saved_geos.pop(request.form['id'])
            session['geos'] = saved_geos
            return f"state dropped: {request.form['id']}"
        except KeyError:
            return f"no such state: {request.form['id']}", 500

    @server.route('/counties-list', methods = ['POST'])
    def counties_list():
        counties_list = geoDB.get_counties(request.form['state'])
        print(request.form['state'])
        return json.dumps(counties_list)
    
    @server.route('/download-data')
    def return_download():
        form = StateForm(request.form)

        data = get_data(
            [[geo['state_name'], geo['county_name']] for id, geo in session['geos'].items()],
            CENSUS_VARS,
            secrets.census_key,
        )

        response = make_response(data.to_csv(index=False))
        response.headers["Content-Disposition"] = "attachment; filename=county_acs_data.csv"
        response.headers["Content-Type"] = "text/csv"

        return response

def render_selected_geo(state, county, id):
    rendered = render_template('selected_geo.html', state = state, county = county, id = id)
    return Markup(rendered)

# if _Name__ == '_Main__':
#     app.run(debug=True)


if __name__ == '__main__':
    server.run(debug=True)
