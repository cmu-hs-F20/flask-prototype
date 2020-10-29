from flask import Flask, render_template, request, session, Markup
from wtforms import Form, TextField, validators
from flask_debugtoolbar import DebugToolbarExtension
from census import get_pop, get_data, get_state_fips, states

import pandas as pd
import dash_table
import dash

import secrets

server = Flask(__name__)
server.secret_key = secrets.app_secret


# DataFrame = pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/solar.csv")
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
    state = TextField('State:', validators = [validators.DataRequired()])

    @server.route('/', methods = ['GET', 'POST'])
    def dashboard():
        form = StateForm(request.form)

        if 'states' not in session:
            session['states'] = {}
            colnames = ['No column data!']
            row_data = ['No row data!']
        else:
            print(session['states'])
            data = get_data(
                [[state['fips'], '*'] for id, state in session['states'].items()],
                ['B01001_001E'],
                secrets.census_key,
            )
  
            colnames = data.columns.values
            row_data = list(data.values.tolist())

        print(form.errors)

        selected_states = []
        for id, state in session['states'].items():
            selected_states.append(render_selected_state(
                id,
                state['state']
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

        saved_states = session.get('states')
        try:
            fips = get_state_fips(request.form['state'])
        except KeyError:
            return f"No such state: {request.form['state']}", 500
        
        saved_states[request.form['id']] = {
            'state': request.form['state'],
            'fips': fips
        }
        session['states'] = saved_states

        return render_selected_state(request.form['id'], request.form['state'])


    @server.route('/drop-geo', methods = ['POST'])
    def drop_geo():

        saved_states = session.get('states')
        try:
            saved_states.pop(request.form['id'])
            session['states'] = saved_states
            return f"state dropped: {request.form['id']}"
        except KeyError:
            return f"no such state: {request.form['id']}", 500

def render_selected_state(id, state):
    rendered = render_template('selected_state.html', state = state, id = id)
    return Markup(rendered)

# if __name__ == '__main__':
#     app.run(debug=True)


if __name__ == '__main__':
    server.run(debug=True)
