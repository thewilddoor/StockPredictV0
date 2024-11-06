import pandas as pd
import numpy as np
from datetime import datetime
from historical_data_fetcher import HistoricalDataFetcher

def process_data(api_response, stock_symbol):
    data = api_response['data']
    current_status = data.get('CurrentStauts', {})
    financial_metrics = data
    news_items = data.get('FinanceNews', [])

    # Fetch historical data using HistoricalDataFetcher
    fetcher = HistoricalDataFetcher(stock_symbol)
    try:
        df = fetcher.fetch_data(period='6mo', interval='1d')
        if df.empty:
            raise ValueError("No historical data found for this stock.")
    except Exception as e:
        raise ValueError(f"Error fetching historical data: {e}")

    # Calculate additional historical metrics
    df.set_index('Date', inplace=True)
    df.sort_index(inplace=True)

    # Calculate moving averages
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()

    # Calculate Relative Strength Index (RSI)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Calculate MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # Extract financial ratios
    financial_ratios = {
        'Current Ratio': financial_metrics.get('currentRatio', {}).get('raw', 0),
        'Quick Ratio': financial_metrics.get('quickRatio', {}).get('raw', 0),
        'Debt to Equity': financial_metrics.get('debtToEquity', {}).get('raw', 0),
        'Return on Assets': financial_metrics.get('returnOnAssets', {}).get('raw', 0),
        'Return on Equity': financial_metrics.get('returnOnEquity', {}).get('raw', 0),
        'Profit Margins': financial_metrics.get('profitMargins', {}).get('raw', 0),
        'Operating Margins': financial_metrics.get('operatingMargins', {}).get('raw', 0),
        'EBITDA Margins': financial_metrics.get('ebitdaMargins', {}).get('raw', 0),
        'Gross Margins': financial_metrics.get('grossMargins', {}).get('raw', 0),
    }

    # Extract growth metrics
    growth_metrics = {
        'Earnings Growth': financial_metrics.get('earningsGrowth', {}).get('raw', 0),
        'Revenue Growth': financial_metrics.get('revenueGrowth', {}).get('raw', 0)
    }

    # Extract cash flow metrics (converted to billions)
    cash_flows = {
        'EBITDA': financial_metrics.get('ebitda', {}).get('raw', 0) / 1e9,
        'Free Cash Flow': financial_metrics.get('freeCashflow', {}).get('raw', 0) / 1e9,
        'Operating Cash Flow': financial_metrics.get('operatingCashflow', {}).get('raw', 0) / 1e9
    }

    # Extract analyst ratings
    analyst_rating = current_status.get('averageAnalystRating', 'N/A')

    # Extract price targets
    price_targets = {
        'Target High Price': financial_metrics.get('targetHighPrice', {}).get('raw', 0),
        'Target Low Price': financial_metrics.get('targetLowPrice', {}).get('raw', 0),
        'Target Mean Price': financial_metrics.get('targetMeanPrice', {}).get('raw', 0),
        'Target Median Price': financial_metrics.get('targetMedianPrice', {}).get('raw', 0),
        'Current Price': current_status.get('regularMarketPrice', {}).get('raw', 0),
    }

    # Extract news titles and publish times
    news_titles = [item['title'] for item in news_items]
    news_publish_times = [datetime.fromtimestamp(item['providerPublishTime']) for item in news_items]

    news_df = pd.DataFrame({
        'Time': news_publish_times,
        'Title': news_titles
    })

    # Technical Rating based on RSI and MACD
    technical_rating = get_technical_rating(df)

    return {
        'stock_name': current_status['longName'],
        'historical_data': df.reset_index(),
        'financial_ratios': financial_ratios,
        'growth_metrics': growth_metrics,
        'cash_flows': cash_flows,
        'price_targets': price_targets,
        'analyst_rating': analyst_rating,
        'technical_rating': technical_rating,
        'news': news_df
    }

def get_technical_rating(df):
    latest_rsi = df['RSI'].iloc[-1]
    latest_macd = df['MACD'].iloc[-1]
    latest_signal = df['Signal_Line'].iloc[-1]

    rating = 'Neutral'

    if latest_rsi < 30 and latest_macd > latest_signal:
        rating = 'Strong Buy'
    elif latest_rsi < 50 and latest_macd > latest_signal:
        rating = 'Buy'
    elif latest_rsi > 70 and latest_macd < latest_signal:
        rating = 'Strong Sell'
    elif latest_rsi > 50 and latest_macd < latest_signal:
        rating = 'Sell'

    return rating
