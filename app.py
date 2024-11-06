# app.py

import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
from coze_api_client import fetch_data
from data_processing import process_data
from historical_data_fetcher import validate_stock_symbol

# Initialize Dash app with a modern Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[
    dbc.themes.LUX,
    "/assets/custom.css"
])
server = app.server  # For deployment

# Define the layout of the app
app.layout = html.Div(className="container", children=[
    # Header
    html.Header([
        html.H1("Stock Analysis Dashboard", className="header-title"),
    ], className="header"),

    # Input Section
    html.Section([
        dbc.InputGroup([
            dbc.Input(
                id='stock-input',
                type='text',
                placeholder='Enter Stock Symbol (e.g., AAPL)',
                className='stock-input'
            ),
            dbc.Button('Submit', id='submit-button', n_clicks=0, color="primary", className='submit-button')
        ], className="input-group"),
    ], className="input-section"),

    # Moving Averages Checklist
    html.Section([
        html.Label('Show Moving Averages:', className="label"),
        dcc.Checklist(
            id='ma-checklist',
            options=[
                {'label': 'MA50', 'value': 'MA50'},
                {'label': 'MA100', 'value': 'MA100'},
                {'label': 'MA200', 'value': 'MA200'}
            ],
            value=[],  # Default: no moving averages displayed
            labelStyle={'display': 'inline-block', 'marginRight': '20px'},
            className="checklist"
        )
    ], className="ma-section"),

    # Loading Spinner
    dcc.Loading(
        id="loading",
        type="circle",
        children=html.Div(id='output-content')
    )
])

@app.callback(
    Output('output-content', 'children'),
    [Input('submit-button', 'n_clicks'),
     Input('ma-checklist', 'value')],
    State('stock-input', 'value')
)
def update_dashboard(n_clicks, ma_values, stock_symbol):
    """
    Update the dashboard based on user inputs.

    :param n_clicks: Number of times the Submit button has been clicked.
    :param ma_values: List of selected moving averages.
    :param stock_symbol: The stock symbol entered by the user.
    :return: Dash HTML components to render.
    """
    if n_clicks > 0 and stock_symbol:
        # Sanitize user input
        stock_symbol = stock_symbol.strip().upper().replace('$', '')

        # Validate stock symbol
        if not validate_stock_symbol(stock_symbol):
            return dbc.Alert(
                "Invalid stock symbol. Please enter a valid symbol and try again.",
                color="danger",
                className="alert"
            )

        # Fetch data using Coze API Client
        api_response = fetch_data(stock_symbol)

        if api_response.get('code') == 200 or api_response.get('code') == 0:
            try:
                # Process data
                data = process_data(api_response, stock_symbol)

                # Ensure required columns exist
                required_columns = ['supertrend', 'direction']
                missing_columns = [col for col in required_columns if col not in data['historical_data'].columns]
                if missing_columns:
                    raise KeyError(f"Missing columns in historical data: {missing_columns}")

                # Create Candlestick and SuperTrend Chart
                fig_price_volume = make_subplots(rows=1, cols=1, shared_xaxes=True,
                                                 subplot_titles=(f"{data['stock_name']} Candlestick Chart with SuperTrend",),
                                                 specs=[[{"secondary_y": False}]])

                # Add Candlestick Trace
                fig_price_volume.add_trace(go.Candlestick(
                    x=data['historical_data']['Date'],
                    open=data['historical_data']['Open'],
                    high=data['historical_data']['High'],
                    low=data['historical_data']['Low'],
                    close=data['historical_data']['Close'],
                    name='Price',
                    increasing_line_color='green',
                    decreasing_line_color='red'
                ), row=1, col=1)

                # Add Moving Averages based on Checklist
                ma_colors = {'MA50': 'blue', 'MA100': 'orange', 'MA200': 'purple'}
                for ma in ma_values:
                    if ma in data['historical_data'].columns:
                        fig_price_volume.add_trace(go.Scatter(
                            x=data['historical_data']['Date'],
                            y=data['historical_data'][ma],
                            mode='lines',
                            name=ma,
                            line=dict(width=1.5, color=ma_colors.get(ma, 'black'))
                        ), row=1, col=1)

                # Separate SuperTrend into Uptrend and Downtrend for coloring
                supertrend_up = data['historical_data'].copy()
                supertrend_up.loc[supertrend_up['direction'] != 1, 'supertrend'] = np.nan

                supertrend_down = data['historical_data'].copy()
                supertrend_down.loc[supertrend_down['direction'] != -1, 'supertrend'] = np.nan

                # Add SuperTrend Uptrend Trace (Green)
                fig_price_volume.add_trace(go.Scatter(
                    x=supertrend_up['Date'],
                    y=supertrend_up['supertrend'],
                    mode='lines',
                    name='Mainly Bullish',
                    line=dict(width=1.5, color='#63b83e'),
                    showlegend=True
                ), row=1, col=1)

                # Add SuperTrend Downtrend Trace (Red)
                fig_price_volume.add_trace(go.Scatter(
                    x=supertrend_down['Date'],
                    y=supertrend_down['supertrend'],
                    mode='lines',
                    name='Mainly Bearish',
                    line=dict(width=1.5, color='#d4222b'),
                    showlegend=True
                ), row=1, col=1)

                # Update Layout with Range Slider and Selector
                fig_price_volume.update_layout(
                    title=f"{data['stock_name']} Candlestick Chart with SuperTrend",
                    xaxis=dict(
                        rangeslider=dict(visible=False),
                        rangeselector=dict(
                            buttons=list([
                                dict(count=1, label='1m', step='month', stepmode='backward'),
                                dict(count=3, label='3m', step='month', stepmode='backward'),
                                dict(count=6, label='6m', step='month', stepmode='backward'),
                                dict(step='all')
                            ])
                        ),
                        type='date'
                    ),
                    yaxis_title='Price',
                    height=800,
                    showlegend=True,
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )

                # Create Financial Ratios Chart
                fig_ratios = px.bar(
                    x=list(data['financial_ratios'].keys()),
                    y=list(data['financial_ratios'].values()),
                    title='Financial Ratios',
                    color=list(data['financial_ratios'].keys()),
                    labels={'x': 'Ratio', 'y': 'Value'},
                    height=400
                )
                fig_ratios.update_layout(showlegend=False, plot_bgcolor='white', paper_bgcolor='white')

                # Create Growth Metrics Chart
                fig_growth = px.bar(
                    x=list(data['growth_metrics'].keys()),
                    y=list(data['growth_metrics'].values()),
                    title='Growth Metrics',
                    color=list(data['growth_metrics'].keys()),
                    labels={'x': 'Metric', 'y': 'Growth (%)'},
                    height=400
                )
                fig_growth.update_layout(showlegend=False, plot_bgcolor='white', paper_bgcolor='white')

                # Create Cash Flow Metrics Chart
                fig_cashflow = px.bar(
                    x=list(data['cash_flows'].keys()),
                    y=list(data['cash_flows'].values()),
                    title='Cash Flow Metrics (in Billions USD)',
                    color=list(data['cash_flows'].keys()),
                    labels={'x': 'Metric', 'y': 'Value (Billions USD)'},
                    height=400
                )
                fig_cashflow.update_layout(showlegend=False, plot_bgcolor='white', paper_bgcolor='white')

                # Create Price Targets Chart
                fig_targets = px.bar(
                    x=list(data['price_targets'].keys()),
                    y=list(data['price_targets'].values()),
                    title='Price Targets and Current Price',
                    color=list(data['price_targets'].keys()),
                    labels={'x': 'Target', 'y': 'Price (USD)'},
                    height=400
                )
                fig_targets.update_layout(showlegend=False, plot_bgcolor='white', paper_bgcolor='white')

                # Create Analyst Rating Display
                analyst_rating_display = dbc.Card(
                    dbc.CardBody([
                        html.H4('Analyst Rating', className="card-title"),
                        html.P(f"Average Analyst Rating: {data['analyst_rating']}", className="card-text")
                    ]),
                    className="analyst-rating-card"
                )

                # Arrange Small Charts in a Grid Layout
                small_charts_layout = html.Div([
                    dbc.Row([
                        dbc.Col(dcc.Graph(figure=fig_ratios, config={'displayModeBar': False}), md=6, className="mb-4"),
                        dbc.Col(dcc.Graph(figure=fig_growth, config={'displayModeBar': False}), md=6, className="mb-4"),
                    ]),
                    dbc.Row([
                        dbc.Col(dcc.Graph(figure=fig_cashflow, config={'displayModeBar': False}), md=6, className="mb-4"),
                        dbc.Col(dcc.Graph(figure=fig_targets, config={'displayModeBar': False}), md=6, className="mb-4"),
                    ])
                ])

                # Combine all charts into a single Div
                charts_content = html.Div([
                    # Candlestick and SuperTrend Chart
                    dbc.Card(
                        dbc.CardBody([
                            dcc.Graph(figure=fig_price_volume, config={'displayModeBar': False})
                        ]),
                        className="chart-card"
                    ),
                    # Analyst Rating
                    analyst_rating_display,
                    # Small Charts Grid
                    small_charts_layout
                ], className="charts-section")

                # Create News Section with Cards
                news_cards = []
                if not data['news'].empty:
                    for index, row in data['news'].iterrows():
                        # Handle missing images
                        image_src = row['Image'] if row['Image'] else 'https://via.placeholder.com/80'
                        # Handle missing links
                        link_href = row['Link'] if row['Link'] else '#'

                        card = dbc.Card(
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col(
                                        html.Img(src=image_src, className="news-image"),
                                        width=2
                                    ),
                                    dbc.Col([
                                        html.H6(
                                            html.A(row['Title'], href=link_href, target='_blank',
                                                   className="news-title"),
                                            className="news-title-heading"
                                        ),
                                        html.P(row['Time'].strftime('%Y-%m-%d'), className="news-time")
                                    ], width=10)
                                ])
                            ]),
                            className="news-card"
                        )
                        news_cards.append(card)
                else:
                    news_cards.append(
                        dbc.Alert(
                            "No news available.",
                            color="info",
                            className="alert"
                        )
                    )

                news_content = html.Div(news_cards, className="news-section")

                # Create Tabs
                tabs = dbc.Tabs([
                    dbc.Tab(label="Charts", tab_id="charts", children=charts_content),
                    dbc.Tab(label="News", tab_id="news", children=news_content),
                ], id="tabs", active_tab="charts", className="mb-3 tabs")

                return tabs

            except KeyError as ke:
                return dbc.Alert(
                    f"Error processing data: Missing column {ke}",
                    color="danger",
                    className="alert"
                )
            except Exception as e:
                return dbc.Alert(
                    f"Error processing data: {str(e)}",
                    color="danger",
                    className="alert"
                )
        else:
            return dbc.Alert(
                f"Error fetching data from API: {api_response.get('msg', 'Unknown error')}",
                color="danger",
                className="alert"
            )
    else:
        return dbc.Alert(
            "Please enter a stock symbol and click Submit.",
            color="secondary",
            className="alert"
        )

if __name__ == '__main__':
    app.run_server(debug=True)
