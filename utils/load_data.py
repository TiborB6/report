import pandas as pd
import os
import json


def load_stock_data(stock_name, path=".", type="daily"):
    """
    Load stock data saved from yfinance (or similar JSON format) into a DataFrame.

    Parameters:
        stock_name (str): Stock symbol (e.g., 'AAPL')
        path (str): Directory containing the JSON file
        type (str): File suffix, e.g., 'daily', 'balance', etc.

    Returns:
        pd.DataFrame: With columns ['open', 'high', 'low', 'close', 'volume']
                     and datetime index (sorted).
    """
    file_path = os.path.join(path, f"{stock_name}_{type}.json")

    # Read JSON as dictionary with date strings as keys
    with open(file_path, "r") as f:
        raw_data = json.load(f)

    # Convert to DataFrame: orient='index' puts date strings as rows
    df = pd.DataFrame.from_dict(raw_data, orient='index')

    # Rename columns to lowercase (optional, but matches your expected output)
    df.rename(columns={
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    }, inplace=True)

    # Keep only the columns we need (ignore Dividends, Stock Splits)
    df = df[['open', 'high', 'low', 'close', 'volume']]

    # Ensure correct data types
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)
    df['volume'] = df['volume'].astype(int)

    # Convert index to datetime and sort
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)

    return df

def load_fundamental_data(symbol, path=".", type="balance"):
    """
    Load fundamental data (balance sheet, income statement, or cash flow) for a symbol.

    Parameters:
    - symbol: stock ticker (e.g., "JPM")
    - path: directory containing the JSON file
    - type: type of fundamental data (e.g., "balance", "income", "cashflow")

    Returns:
    - DataFrame with fiscal year as index and metrics as columns
    """
    file_path = os.path.join(path, f"{symbol}_{type}.json")

    with open(file_path, "r") as f:
        data = json.load(f)

    reports = data["quarterlyReports"]

    df = pd.DataFrame(reports)

    df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
    df.set_index("fiscalDateEnding", inplace=True)
    df.sort_index(inplace=True)

    for col in df.columns:
        if col == "reportedCurrency":
            continue
        df[col] = pd.to_numeric(df[col], errors='coerce')   # <-- fixed

    return df