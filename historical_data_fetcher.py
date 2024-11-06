# historical_data_fetcher.py

import yfinance as yf
import pandas as pd

class HistoricalDataFetcher:
    def __init__(self, stock_symbol):
        self.stock_symbol = stock_symbol.upper()
        self.data = None

    def fetch_data(self, period='1y', interval='1d'):
        """
        Fetch historical data for the stock symbol.
        :param period: The period to fetch data for (e.g., '120d' for 120 days).
        :param interval: The data interval (e.g., '1d' for daily data).
        :return: Pandas DataFrame with historical data.
        """
        ticker = yf.Ticker(self.stock_symbol)
        self.data = ticker.history(period=period, interval=interval)
        if self.data.empty:
            raise ValueError("No historical data found for this stock.")
        self.data.reset_index(inplace=True)
        self.data.rename(columns={
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume',
            'Date': 'Date'
        }, inplace=True)
        return self.data

def validate_stock_symbol(stock_symbol):
    """
    Validates if the stock symbol exists by attempting to fetch its historical data.
    :param stock_symbol: The stock symbol to validate.
    :return: True if valid, False otherwise.
    """
    ticker = yf.Ticker(stock_symbol)
    try:
        data = ticker.history(period='1d')
        if data.empty:
            return False
        else:
            return True
    except Exception:
        return False
    
