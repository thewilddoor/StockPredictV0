# data_processing.py

import pandas as pd
import numpy as np
from datetime import datetime
from historical_data_fetcher import HistoricalDataFetcher

def process_data(api_response, stock_symbol):
    """
    Process the API response and calculate necessary metrics.

    :param api_response: JSON response from the API containing stock data.
    :param stock_symbol: The stock symbol being analyzed.
    :return: Dictionary containing processed data.
    """
    data = api_response.get('data', {})
    current_status = data.get('CurrentStauts', {})
    financial_metrics = data
    news_items = data.get('FinanceNews', [])

    # Fetch historical data using HistoricalDataFetcher
    fetcher = HistoricalDataFetcher(stock_symbol)
    try:
        df = fetcher.fetch_data(period='2y', interval='1d')
    except Exception as e:
        raise ValueError(f"Error fetching historical data: {e}")

    # Calculate additional historical metrics
    df.set_index('Date', inplace=True)
    df.sort_index(inplace=True)

    # Calculate moving averages (MA50, MA100, MA200)
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['MA100'] = df['Close'].rolling(window=100).mean()
    df['MA200'] = df['Close'].rolling(window=200).mean()

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

    # Extract news data
    news_titles = []
    news_publish_times = []
    news_links = []
    news_images = []

    for item in news_items:
        # Ensure item is a dictionary
        if not isinstance(item, dict):
            continue

        # Title
        title = item.get('title', 'No Title')
        news_titles.append(title)

        # Publish Time
        provider_publish_time = item.get('providerPublishTime')
        if provider_publish_time:
            try:
                publish_time = datetime.fromtimestamp(provider_publish_time)
            except Exception:
                publish_time = datetime.now()
        else:
            publish_time = datetime.now()
        news_publish_times.append(publish_time)

        # Link
        link = item.get('link', '')
        news_links.append(link)

        # Image
        thumbnail = item.get('thumbnail', {})
        image_url = ''
        if isinstance(thumbnail, dict):
            resolutions = thumbnail.get('resolutions', [])
            if resolutions and isinstance(resolutions, list):
                last_resolution = resolutions[-1]
                if isinstance(last_resolution, dict):
                    image_url = last_resolution.get('url', '')
        news_images.append(image_url)

    news_df = pd.DataFrame({
        'Time': news_publish_times,
        'Title': news_titles,
        'Link': news_links,
        'Image': news_images
    })

    # Calculate SuperTrend
    supertrend_data = calculate_supertrend(df.reset_index(), atr_period=4, factor=2.94, reset_period=30)

    # Merge SuperTrend data into df
    df = df.reset_index().merge(supertrend_data[['Date', 'supertrend', 'direction']], on='Date', how='left')
    df.set_index('Date', inplace=True)

    return {
        'stock_name': current_status.get('longName', stock_symbol),
        'historical_data': df.reset_index(),
        'financial_ratios': financial_ratios,
        'growth_metrics': growth_metrics,
        'cash_flows': cash_flows,
        'price_targets': price_targets,
        'analyst_rating': analyst_rating,
        'news': news_df
    }


def calculate_supertrend(df, atr_period=4, factor=2.94, reset_period=10):
    """
    Calculate the SuperTrend indicator with recalculation every reset_period days.

    :param df: Pandas DataFrame with historical OHLCV data.
    :param atr_period: ATR period.
    :param factor: Multiplier for ATR.
    :param reset_period: Number of days after which to reset SuperTrend calculation.
    :return: DataFrame with SuperTrend and Direction.
    """
    # Ensure Date is in datetime format
    df['Date'] = pd.to_datetime(df['Date'])

    # Calculate True Range (TR)
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = df[['High', 'Low', 'previous_close']].apply(
        lambda x: max(x['High'] - x['Low'], abs(x['High'] - x['previous_close']), abs(x['Low'] - x['previous_close'])), axis=1
    )

    # Calculate ATR as the Exponential Moving Average of TR
    df['ATR'] = df['TR'].ewm(span=atr_period, adjust=False).mean()

    # Calculate HL2
    df['HL2'] = (df['High'] + df['Low']) / 2

    # Calculate Basic Upper and Lower Bands
    df['UpperBasic'] = df['HL2'] + (factor * df['ATR'])
    df['LowerBasic'] = df['HL2'] - (factor * df['ATR'])

    # Initialize Final Upper and Lower Bands
    df['UpperBand'] = 0.0
    df['LowerBand'] = 0.0

    # Initialize SuperTrend and Direction
    df['supertrend'] = np.nan
    df['direction'] = 1  # 1 for uptrend, -1 for downtrend

    for current in range(len(df)):
        if current == 0 or (current % reset_period == 0):
            # Reset SuperTrend calculation every reset_period days
            df.at[current, 'UpperBand'] = df.at[current, 'UpperBasic']
            df.at[current, 'LowerBand'] = df.at[current, 'LowerBasic']
            df.at[current, 'supertrend'] = df.at[current, 'UpperBand']
            df.at[current, 'direction'] = 1  # Start with uptrend
            continue

        # Final Upper Band
        if df.at[current, 'UpperBasic'] < df.at[current - 1, 'UpperBand'] or df.at[current - 1, 'Close'] > df.at[current - 1, 'supertrend']:
            df.at[current, 'UpperBand'] = df.at[current, 'UpperBasic']
        else:
            df.at[current, 'UpperBand'] = df.at[current - 1, 'UpperBand']

        # Final Lower Band
        if df.at[current, 'LowerBasic'] > df.at[current - 1, 'LowerBand'] or df.at[current - 1, 'Close'] < df.at[current - 1, 'supertrend']:
            df.at[current, 'LowerBand'] = df.at[current, 'LowerBasic']
        else:
            df.at[current, 'LowerBand'] = df.at[current - 1, 'LowerBand']

        # Determine direction
        if (df.at[current - 1, 'Close'] <= df.at[current - 1, 'supertrend']) and (df.at[current, 'Close'] > df.at[current, 'UpperBand']):
            df.at[current, 'direction'] = 1  # Uptrend
        elif (df.at[current - 1, 'Close'] >= df.at[current - 1, 'supertrend']) and (df.at[current, 'Close'] < df.at[current, 'LowerBand']):
            df.at[current, 'direction'] = -1  # Downtrend
        else:
            df.at[current, 'direction'] = df.at[current - 1, 'direction']

        # Assign SuperTrend value
        if df.at[current, 'direction'] == 1:
            df.at[current, 'supertrend'] = df.at[current, 'LowerBand']
        else:
            df.at[current, 'supertrend'] = df.at[current, 'UpperBand']

    # Clean up
    df.drop(['previous_close', 'TR', 'UpperBasic', 'LowerBasic', 'UpperBand', 'LowerBand'], axis=1, inplace=True)

    # Fill initial NaN SuperTrend values
    df['supertrend'].fillna(method='bfill', inplace=True)

    return df[['Date', 'supertrend', 'direction']]
