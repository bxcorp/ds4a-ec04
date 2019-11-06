import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import dash_table
import os
from sqlalchemy import create_engine

# username = os.environ.get('DB_USER')
# password = os.environ.get('DB_USER_PASSWORD')
# host = os.environ.get('DB_HOST')
# port = '5432'
# database = os.environ.get('DB_APP_PYTHON')

# engine = create_engine(f'postgresql://{username}:{password}@{host}:{port}/{database}', echo=False)
# df = pd.read_sql("SELECT * from trades", engine.connect(), parse_dates=('Entry time',))

df = pd.read_csv('aggr.csv', parse_dates=['Entry time'])

app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/uditagarwal/pen/oNvwKNP.css', 'https://codepen.io/uditagarwal/pen/YzKbqyV.css'])

app.layout = html.Div(children=[
    html.Div(
        children=[
            html.H2(children="Bitcoin Leveraged Trading Backtest Analysis", className='h2-title'),
        ],
        className='study-browser-banner row'
    ),
    html.Div(
        className="row app-body",
        children=[
            html.Div(
                className="twelve columns card",
                children=[
                    html.Div(
                        className="padding row",
                        children=[
                            html.Div(
                                className="two columns card",
                                children=[
                                    html.H6("Select Exchange", ),
                                    dcc.RadioItems(
                                        id="exchange-select",
                                        options=[
                                            {'label': label, 'value': label} for label in df['Exchange'].unique()
                                        ],
                                        value='Bitmex',
                                        labelStyle={'display': 'inline-block'}
                                    )
                                ]
                            ),
                            html.Div(
                                className="two columns card 2",
                                children=[
                                    html.H6("Select Leverage: ", ),
                                    dcc.RadioItems(
                                        id="leverage-select",
                                        options=[
                                            {'label': label, 'value': label} for label in df['Margin'].unique()
                                        ],
                                        value=1,
                                        labelStyle={'display': 'inline-block'}
                                    )
                                ]
                            ),
                            html.Div(
                                className="three columns card",
                                children=[
                                    html.H6("Select a date range: ", ),
                                    dcc.DatePickerRange(
                                        id="date-range",
                                        display_format="MMM YY",
                                        start_date=df['Entry time'].min(),
                                        end_date=df['Entry time'].max()
                                    )
                                ]
                            ),
                            html.Div(
                                id="strat-returns-div",
                                className="two columns indicator pretty_container",
                                children=[
                                    html.P(id="strat-returns", className="indicator_value"),
                                    html.P('Strategy Returns', className="twelve columns indicator_text"),
                                ]
                            ),
                            html.Div(
                                id="market-returns-div",
                                className="two columns indicator pretty_container",
                                children=[
                                    html.P(id="market-returns", className="indicator_value"),
                                    html.P('Market Returns', className="twelve columns indicator_text"),
                                ]
                            ),
                            html.Div(
                                id="strat-vs-market-div",
                                className="two columns indicator pretty_container",
                                children=[
                                    html.P(id="strat-vs-market", className="indicator_value"),
                                    html.P('Strategy vs. Market Returns', className="twelve columns indicator_text"),
                                ]
                            ),
                            html.Div(
                                className="twelve columns card",
                                children=[
                                    dcc.Graph(
                                        id="monthly-chart",
                                        figure={
                                            'data': []
                                        }
                                    )
                                ]
                            ),
                            html.Div(
                                className="padding row",
                                children=[
                                    html.Div(
                                        className="six columns card",
                                        children=[
                                            dash_table.DataTable(
                                                id='table',
                                                columns=[
                                                    {'name': 'Number', 'id': 'Number'},
                                                    {'name': 'Trade type', 'id': 'Trade type'},
                                                    {'name': 'Exposure', 'id': 'Exposure'},
                                                    {'name': 'Entry balance', 'id': 'Entry balance'},
                                                    {'name': 'Exit balance', 'id': 'Exit balance'},
                                                    {'name': 'Pnl (incl fees)', 'id': 'Pnl (incl fees)'},
                                                ],
                                                style_cell={'width': '50px'},
                                                style_table={
                                                    'maxHeight': '450px',
                                                    'overflowY': 'scroll'
                                                },
                                            )
                                        ]
                                    ),
                                    dcc.Graph(
                                        id="pnl-types",
                                        className="six columns card",
                                        figure={},
                                        style={'height': '450px'}
                                    )
                                ]
                            ),
                            html.Div(
                                className="padding row",
                                children=[
                                    dcc.Graph(
                                        id="daily-btc",
                                        className="six columns card",
                                        figure={},
                                        style={'height': '450px'}
                                    ),
                                    dcc.Graph(
                                        id="balance",
                                        className="six columns card",
                                        figure={},
                                        style={'height': '450px'}
                                    )
                                ]
                            )
                        ]
                    )
                ]
            )
        ]
    )
])


# ==========================Exercise 3==========================
@app.callback(
    [
        dash.dependencies.Output('date-range', 'start_date'),
        dash.dependencies.Output('date-range', 'end_date')
    ],
    [
        dash.dependencies.Input('exchange-select', 'value'),
    ]
)
def update_start_end_dates(value):
    return df[df['Exchange'] == value]['Entry time'].min(), df[df['Exchange'] == value]['Entry time'].max()


# ==========================Exercise 4==========================
def filter_df(dff, exchange, margin, start_date, end_date):
    dff = dff[(dff['Exchange'] == exchange) &
              (dff['Margin'] == margin) &
              (dff['Entry time'] >= start_date) &
              (dff['Entry time'] <= end_date)]

    dff['YearMonth'] = pd.to_datetime(dff['Entry time'].dt.strftime('%b %Y'))
    return dff


# ==========================Exercise 5==========================
@app.callback(
    [
        dash.dependencies.Output('monthly-chart', 'figure'),
        dash.dependencies.Output('market-returns', 'children'),
        dash.dependencies.Output('strat-returns', 'children'),
        dash.dependencies.Output('strat-vs-market', 'children'),
    ],
    (
            dash.dependencies.Input('exchange-select', 'value'),
            dash.dependencies.Input('leverage-select', 'value'),
            dash.dependencies.Input('date-range', 'start_date'),
            dash.dependencies.Input('date-range', 'end_date'),
    )
)
def update_monthly(exchange, margin, start_date, end_date):
    dff = filter_df(df, exchange, margin, start_date, end_date)

    rows = calc_returns_over_month(dff)
    btc_returns = calc_btc_returns(dff)
    strat_returns = calc_strat_returns(dff)
    strat_vs_market = strat_returns - btc_returns

    return {
        'data': [
            go.Candlestick(
                open=[data['entry'] for data in rows],
                close=[data['exit'] for data in rows],
                x=[data['month'] for data in rows],
                low=[data['entry'] for data in rows],
                high=[data['exit'] for data in rows]
            )
        ],
        'layout': {
            'title': 'Overview of Monthly performance'
        }
    }, f'{btc_returns:0.2f}%', f'{strat_returns:0.2f}%', f'{strat_vs_market:0.2f}%'


def calc_returns_over_month(dff):
    result = []

    for name, group in dff.groupby('YearMonth'):
        exit_value = group.head(1)['Exit balance'].values[0]
        entry_value = group.tail(1)['Entry balance'].values[0]
        monthly_value = (exit_value * 100 / entry_value) - 100
        result.append({
            'month': name,
            'entry': entry_value,
            'exit': exit_value,
            'monthly_return': monthly_value
        })
    return result


def calc_btc_returns(dff):
    btc_start_value = dff.tail(1)['BTC Price'].values[0]
    btc_end_value = dff.head(1)['BTC Price'].values[0]
    btc_returns = (btc_end_value * 100 / btc_start_value) - 100
    return btc_returns


def calc_strat_returns(dff):
    start_value = dff.tail(1)['Exit balance'].values[0]
    end_value = dff.head(1)['Entry balance'].values[0]
    returns = (end_value * 100 / start_value) - 100
    return returns


# ==========================Exercise 6==========================
@app.callback(
    dash.dependencies.Output('pnl-types', 'figure'),
    (
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range', 'start_date'),
        dash.dependencies.Input('date-range', 'end_date'),
    )
)
def update_bar_chart(exchange, margin, start_date, end_date):
    dff = filter_df(df, exchange, margin, start_date, end_date)
    return {
        'data': calc_pnl_trade_type(dff),
        'layout': {
            'title': {
                'text': 'PnL vs Trade type',
            }
        }
    }


def calc_pnl_trade_type(dff):
    data = []

    for name, group in df.groupby('Trade type'):
        data.append(
            go.Bar(y=group['Pnl (incl fees)'], x=group['Entry time'].sort_values(), name=name, orientation='v')
        )
    return data


# ==========================Exercise 7==========================
@app.callback(
    dash.dependencies.Output('daily-btc', 'figure'),
    [
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range', 'start_date'),
        dash.dependencies.Input('date-range', 'end_date'),
    ]
)
def update_price_btc(exchange, margin, start_date, end_date):
    dff = filter_df(df, exchange, margin, start_date, end_date)

    return {
        'data': calc_price_btc(dff),
        'layout': {
            'title': {
                'text': 'Daily BTC Price'
            }
        }
    }


def calc_price_btc(dff):
    data = [go.Scatter(x=dff['Entry time'], y=dff['BTC Price'])]
    return data


@app.callback(
    dash.dependencies.Output('balance', 'figure'),
    [
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range', 'start_date'),
        dash.dependencies.Input('date-range', 'end_date'),
    ]
)
def update_portfolio_balance(exchange, margin, start_date, end_date):
    dff = filter_df(df, exchange, margin, start_date, end_date)

    return {
        'data': calc_portfolio_balance(dff),
        'layout': {
            'title': {
                'text': 'Daily BTC Price'
            }
        }
    }


def calc_portfolio_balance(dff):
    data = [go.Scatter(x=dff['Entry time'], y=dff['Exit balance'])]
    return data


# ==========================GIVEN CODE==========================
@app.callback(
    dash.dependencies.Output('table', 'data'),
    (
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range', 'start_date'),
        dash.dependencies.Input('date-range', 'end_date'),
    )
)
def update_table(exchange, leverage, start_date, end_date):
    dff = filter_df(df, exchange, leverage, start_date, end_date)
    return dff.to_dict('records')


if __name__ == "__main__":
    app.run_server(debug=True)
