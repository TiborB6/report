import pandas as pd

def calculate_financial_metrics(stock_df, fundamental_df, overview_df):
    """
    Compute key metrics from stock and fundamental data.
    Returns a dictionary of metric names and formatted values.
    """
    # Ensure data is sorted
    stock_sorted = stock_df.sort_values('fiscalDateEnding')
    fund_sorted = fundamental_df.sort_values('fiscalDateEnding')

    # Latest data
    latest_stock = stock_sorted.iloc[-1]
    latest_fund = fund_sorted.iloc[-1] if not fund_sorted.empty else None

    # 1. 2-Week Price Range (high - low over last 14 trading days)
    two_weeks = stock_sorted.tail(14)
    price_range = two_weeks['high'].max() - two_weeks['low'].min()
    price_range_str = f"{price_range:.2f}"

    # 2. Shares Outstanding (B) – shares outstanding in billions
    if latest_fund is not None and 'commonStockSharesOutstanding' in latest_fund:
        shares_out = latest_fund['commonStockSharesOutstanding'] / 1e9
        shares_str = f"{shares_out:.2f}"
    else:
        shares_str = "N/A"

    # 3. Dividend Per Share – from fundamental data if available
    # Many APIs provide 'dividendPerShare'. Here we assume it's missing -> 0.
    # If you have 'dividendPayoutCommonStock' and shares outstanding, you could compute.
    div_per_share = 0.0  # placeholder – replace with actual field if exists
    div_per_share_str = f"{div_per_share:.2f}"

    # 4. $10K Invested 5 Years Ago – need price 5 years ago vs today
    today_price = latest_stock['close']
    # Find closest date ~5 years ago from today
    five_years_ago = latest_stock['fiscalDateEnding'] - pd.DateOffset(years=5)
    # Get the closest available price (or NaN)
    past_prices = stock_sorted[stock_sorted['fiscalDateEnding'] <= five_years_ago]
    if not past_prices.empty:
        past_price = past_prices.iloc[-1]['close']
        value_today = 10000 * (today_price / past_price)
        invest_str = f"{value_today:,.2f}"
    else:
        invest_str = "N/A"

    # 5. Market Cap (B) – market cap in billions
    if latest_fund is not None and 'commonStockSharesOutstanding' in latest_fund:
        market_cap = (latest_stock['close'] * latest_fund['commonStockSharesOutstanding']) / 1e9
        market_cap_str = f"{market_cap:.2f}"
    else:
        market_cap_str = "N/A"

    # 6. Dividend Yield (%) – annual dividend / price
    # Assuming annual dividend = dividend per share * 4 (if quarterly) – adjust accordingly
    # Here we use div_per_share as annual.
    if div_per_share > 0 and today_price > 0:
        div_yield = (div_per_share / today_price) * 100
        div_yield_str = f"{div_yield:.2f}%"
    else:
        div_yield_str = "0%"

    # 7. Avg Daily Volume (M) – average volume in millions
    avg_volume = stock_sorted['volume'].mean() / 1e6
    avg_volume_str = f"{avg_volume:.2f}"

    # 8. Beta – you need market data to compute; use provided value or placeholders
    # We'll use a variable; if you have a function to compute beta, insert here.
    beta = 1.36  # example – replace with your calculation or external input
    beta_str = f"{beta:.2f}"
    moody_rating = "Caa1"

    metrics = {
        "2-Week Price Range": price_range_str,
        "Shares Outstanding (B)": shares_str,
        "Dividend Per Share": div_per_share_str,
        "10K Invested 5 Years Ago": invest_str,
        "Market Cap (B)": market_cap_str,
        "Dividend Yield": overview_df['DividendPerShare'],
        "Avg Daily Volume (M)": avg_volume_str,
        "Beta": overview_df['Beta'],
    }
    return metrics