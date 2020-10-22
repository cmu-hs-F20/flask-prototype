from flask import Flask
import pandas as pd
import dash_table
import dash

server = Flask(__name__)


@server.route('/')
def hello_world():
    return 'Hello World!'


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

if __name__ == '__main__':
    app.run_server()
