import pandas as pd
from pathlib import Path
import yfinance as yf

def get_competitors(ticker, use_top_n=5):
    """
    Returns a list of competitor tickers based on:
    1. Same sector as the target company
    2. Closest market cap (absolute difference) within that sector
    """
    file_path = Path.cwd() / "nasdaq_screener_1778886856653.csv"
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    df = pd.read_csv(file_path)

    if df['Market Cap'].dtype == 'object':
        df['Market Cap'] = df['Market Cap'].str.replace(',', '').astype(float)
    else:
        df['Market Cap'] = df['Market Cap'].astype(float)

    target = df[df['Symbol'] == ticker]
    if target.empty:
        raise ValueError(f"Ticker '{ticker}' not found.")

    target_mcap = target['Market Cap'].values[0]
    target_sector = target['Sector'].values[0] if 'Sector' in df.columns else None

    if target_sector is None:
        raise KeyError("Column 'Sector' not found in the CSV. Please ensure the file contains sector information.")

    same_sector = df[(df['Sector'] == target_sector) & (df['Symbol'] != ticker)].copy()

    if same_sector.empty:
        return []

    same_sector['CapDiff'] = (same_sector['Market Cap'] - target_mcap).abs()
    top_tickers = same_sector.sort_values('CapDiff').head(use_top_n)['Symbol'].tolist()

    return top_tickers