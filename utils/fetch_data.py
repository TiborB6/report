import requests
import json
import time
import os
import yfinance as yf

def fetch_and_save_single_endpoint(symbol, endpoint_name, endpoint_params, api_key):
    """
    Fetch data for one endpoint from Alpha Vantage and save it as a JSON file.

    Parameters:
        symbol (str): Stock symbol.
        endpoint_name (str): Name of the endpoint (e.g., 'balance').
        endpoint_params (dict): Contains 'function', 'file_suffix', and optionally 'full_history'.
        api_key (str): Alpha Vantage API key.

    Returns:
        str or None: File path if successful, else None.
    """
    # Build URL
    url = (f"https://www.alphavantage.co/query"
           f"?function={endpoint_params['function']}"
           f"&symbol={symbol}&apikey={api_key}")
    if endpoint_params.get('full_history', False):
        url += "&outputsize=full"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if 'Error Message' in data:
            print(f"API error for {endpoint_name}: {data['Error Message']}")
            return None
        if 'Note' in data:
            print(f"API note for {endpoint_name}: {data['Note']}")
            return None

        filename = f"{symbol}_{endpoint_params['file_suffix']}.json"
        filepath = os.path.join(os.getcwd(), filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Saved: {filepath}")
        return filepath

    except Exception as e:
        print(f"Failed to fetch/save {endpoint_name}: {e}")
        return None

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
    endpoints = {
        'balance': {'function': 'BALANCE_SHEET', 'file_suffix': 'balance', 'full_history': False},
        'earnings': {'function': 'INCOME_STATEMENT', 'file_suffix': 'earnings', 'full_history': False},
        'cash': {'function': 'CASH_FLOW', 'file_suffix': 'cash', 'full_history': False},
        'overview': {'function': 'OVERVIEW', 'file_suffix': 'overview', 'full_history': False},
    }

    saved_files = []
    endpoint_items = list(endpoints.items())

    for idx, (endpoint_name, params) in enumerate(endpoint_items):
        filepath = fetch_and_save_single_endpoint(symbol, endpoint_name, params, api_key)
        if filepath:
            saved_files.append(filepath)

        # Sleep between calls (10 seconds) except after the last one
        if idx != len(endpoint_items) - 1:
            time.sleep(2)

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

def cleanup(directory_path="."):
    """
    Delete the following files in the specified directory:
    - .json
    - .tex
    - .log
    - .aux
    - .pdf files that are NOT named 'report.pdf'
    """
    if not os.path.isdir(directory_path):
        raise ValueError(f"Directory not found: {directory_path}")

    deleted = 0
    errors = 0

    for filename in os.listdir(directory_path):
        # Determine if the file should be removed
        should_remove = False

        if filename.endswith((".json", ".tex", ".log", ".aux")):
            should_remove = True
        elif filename.endswith(".pdf") and filename != "report.pdf":
            should_remove = True

        if should_remove:
            file_path = os.path.join(directory_path, filename)
            try:
                os.remove(file_path)
                deleted += 1
                print(f"Deleted: {file_path}")
            except Exception as e:
                errors += 1
                print(f"Error deleting {file_path}: {e}")

    return deleted, errors