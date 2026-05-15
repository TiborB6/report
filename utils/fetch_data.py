import requests
import json
import time
import os
import yfinance as yf

def fetch_financial_data(symbol, api_key='demo'):
    """
    Fetch raw JSON data from Alpha Vantage for a given symbol and save each
    response as a JSON file in the current working directory.

    Parameters:
        symbol (str): Stock symbol (e.g., 'IBM').
        api_key (str): Alpha Vantage API key. Defaults to 'demo'.

    Returns:
        list: A list of file paths (strings) where the JSON data was saved.
    """
    base_url = 'https://www.alphavantage.co/query'
    endpoints = {
        'balance': {'function': 'BALANCE_SHEET', 'file_suffix': 'balance', 'full_history': False},
        'earnings': {'function': 'INCOME_STATEMENT', 'file_suffix': 'earnings', 'full_history': False},
        'cash': {'function': 'CASH_FLOW', 'file_suffix': 'cash', 'full_history': False}
    }

    saved_files = []

    for idx, (endpoint_name, params) in enumerate(endpoints.items()):
        # Build URL with outputsize for stock endpoint
        url = f"{base_url}?function={params['function']}&symbol={symbol}&apikey={api_key}"
        if params.get('full_history', False):
            url += "&outputsize=full"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            if 'Error Message' in data:
                print(f"API error for {endpoint_name}: {data['Error Message']}")
                continue
            if 'Note' in data:
                print(f"API note for {endpoint_name}: {data['Note']}")
                continue

            filename = f"{symbol}_{params['file_suffix']}.json"
            filepath = os.path.join(os.getcwd(), filename)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

            saved_files.append(filepath)
            print(f"Saved: {filepath}")

        except Exception as e:
            print(f"Failed to fetch/save {endpoint_name}: {e}")

        if idx != len(endpoints) - 1:
            time.sleep(10)

    return saved_files

def fetch_financial_data_yfinance(symbol, period='5y'):
    """
    Fetch historical prices and financial statements using yfinance
    and save each as a JSON file in the current working directory.

    Parameters:
        symbol (str): Stock symbol (e.g., 'IBM').
        period (str): Valid periods: '1d', '5d', '1mo', '3mo', '6mo',
                      '1y', '2y', '5y', '10y', 'ytd', 'max'. Default '5y'.

    Returns:
        list: A list of file paths (strings) where the JSON data was saved.
    """
    ticker = yf.Ticker(symbol)
    saved_files = []

    # 1. Historical prices (daily)
    hist = ticker.history(period=period)
    if not hist.empty:
        # Convert DataFrame to JSON (orient='index' keeps date as key)
        hist_json = hist.to_json(orient='index', date_format='iso')
        filename = f"{symbol}_daily.json"
        filepath = os.path.join(os.getcwd(), filename)
        with open(filepath, 'w') as f:
            json.dump(json.loads(hist_json), f, indent=2)  # pretty print
        saved_files.append(filepath)
        print(f"Saved: {filepath}")
    else:
        print(f"No historical data for {symbol}")

    return saved_files