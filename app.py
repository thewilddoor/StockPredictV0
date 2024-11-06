# app.py

import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go

from coze_api_client import fetch_data
from data_processing import process_data
from historical_data_fetcher import validate_stock_symbol

# Initialize Dash app
app = dash.Dash(__name__)
server = app.server  # For deployment

app.layout = html.Div(style={'margin': '40px'}, children=[
    html.H1("Stock Analysis Dashboard", style={'textAlign': 'center'}),

    # Input for Stock Symbol
    html.Div([
        dcc.Input(
            id='stock-input',
            type='text',
            placeholder='Enter Stock Symbol (e.g., AAPL)',
            style={'width': '200px'}
        ),
        html.Button('Submit', id='submit-button', n_clicks=0)
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),

    html.Div(id='output-content')
])

@app.callback(
    Output('output-content', 'children'),
    Input('submit-button', 'n_clicks'),
    State('stock-input', 'value')
)
def update_dashboard(n_clicks, stock_symbol):
    if n_clicks > 0 and stock_symbol:
        # Sanitize user input
        stock_symbol = stock_symbol.strip().upper().replace('$', '')

        # Validate stock symbol
        if not validate_stock_symbol(stock_symbol):
            return html.Div([
                html.H3('Invalid stock symbol. Please enter a valid symbol and try again.')
            ])

        # Fetch data using Coze API Client
        api_response = fetch_data(stock_symbol)

        if api_response.get('code') == 200 or api_response.get('code') == 0:
            # Process data
            data = process_data(api_response, stock_symbol)

            # (The rest of the code remains the same as before)
            # Create figures
            figures = []

            # Stock Price and Moving Averages
            fig_price = go.Figure()
            fig_price.add_trace(go.Scatter(
                x=data['historical_data']['Date'], y=data['historical_data']['Close'],
                mode='lines', name='Close Price'
            ))
            fig_price.add_trace(go.Scatter(
                x=data['historical_data']['Date'], y=data['historical_data']['MA10'],
                mode='lines', name='MA10'
            ))
            fig_price.add_trace(go.Scatter(
                x=data['historical_data']['Date'], y=data['historical_data']['MA20'],
                mode='lines', name='MA20'
            ))
            fig_price.add_trace(go.Scatter(
                x=data['historical_data']['Date'], y=data['historical_data']['MA50'],
                mode='lines', name='MA50'
            ))
            fig_price.update_layout(title=f"{data['stock_name']} Stock Price with Moving Averages")

            figures.append(dcc.Graph(figure=fig_price))

            # RSI Chart
            fig_rsi = px.line(
                data['historical_data'], x='Date', y='RSI',
                title='Relative Strength Index (RSI)'
            )
            figures.append(dcc.Graph(figure=fig_rsi))

            # MACD Chart
            fig_macd = go.Figure()
            fig_macd.add_trace(go.Scatter(
                x=data['historical_data']['Date'], y=data['historical_data']['MACD'],
                mode='lines', name='MACD'
            ))
            fig_macd.add_trace(go.Scatter(
                x=data['historical_data']['Date'], y=data['historical_data']['Signal_Line'],
                mode='lines', name='Signal Line'
            ))
            fig_macd.update_layout(title='Moving Average Convergence Divergence (MACD)')
            figures.append(dcc.Graph(figure=fig_macd))

            # Volume Over Time
            fig_volume = px.bar(
                data['historical_data'],
                x='Date',
                y='Volume',
                title='Trading Volume Over Time'
            )
            figures.append(dcc.Graph(figure=fig_volume))

            # Financial Ratios
            fig_ratios = px.bar(
                x=list(data['financial_ratios'].keys()),
                y=list(data['financial_ratios'].values()),
                title='Financial Ratios'
            )
            figures.append(dcc.Graph(figure=fig_ratios))

            # Growth Metrics
            fig_growth = px.bar(
                x=list(data['growth_metrics'].keys()),
                y=list(data['growth_metrics'].values()),
                title='Growth Metrics'
            )
            figures.append(dcc.Graph(figure=fig_growth))

            # Cash Flow Metrics
            fig_cashflow = px.bar(
                x=list(data['cash_flows'].keys()),
                y=list(data['cash_flows'].values()),
                title='Cash Flow Metrics (in Billions USD)'
            )
            figures.append(dcc.Graph(figure=fig_cashflow))

            # Price Targets
            fig_targets = px.bar(
                x=list(data['price_targets'].keys()),
                y=list(data['price_targets'].values()),
                title='Price Targets and Current Price'
            )
            figures.append(dcc.Graph(figure=fig_targets))

            # Technical Rating
            figures.append(html.Div([
                html.H2('Technical Rating'),
                html.P(f"The current technical rating is: {data['technical_rating']}", style={'fontSize': '24px'})
            ], style={'marginTop': '20px'}))

            # Analyst Rating
            figures.append(html.Div([
                html.H2('Analyst Rating'),
                html.P(f"Average Analyst Rating: {data['analyst_rating']}", style={'fontSize': '18px'})
            ], style={'marginTop': '20px'}))

            # Latest Financial News
            news_items = html.Ul([
                html.Li(f"{row['Time'].strftime('%Y-%m-%d')}: {row['Title']}")
                for index, row in data['news'].iterrows()
            ])

            figures.append(html.Div([
                html.H2('Latest Financial News'),
                news_items
            ], style={'marginTop': '20px', 'fontSize': '18px'}))

            return figures
        else:
            return html.Div([
                html.H3('Error fetching data. Please check the stock symbol and try again.'),
                html.P(f"Error Message: {api_response.get('msg', 'Unknown error')}")
            ])
    else:
        return html.Div([
            html.H3('Please enter a stock symbol and click Submit.')
        ])

if __name__ == '__main__':
    app.run_server(debug=True)
