import pandas as pd

def key_figures(fundamental_stock, n=5):
    df = fundamental_stock.copy()   # work on a copy
    df['EPS'] = df['netIncome_x'] / df['commonStockSharesOutstanding']
    df['FCF'] = df['operatingCashflow'] - df['capitalExpenditures']
    df['FCFPS'] = df['FCF'] / df['commonStockSharesOutstanding']
    df['PE_Ratio'] = df['close'] / df['EPS']
    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    first_per_year = df.groupby('year').first().reset_index()
    last5_years = sorted(first_per_year['year'].unique())[-n:]
    metrics = ['close', 'EPS', 'PE_Ratio', 'FCFPS']
    wide_df = first_per_year[first_per_year['year'].isin(last5_years)].set_index('year')[metrics].T
    return wide_df.round(2)


def key_growth_rates(fundamental_stock):
    # Work on a copy to avoid mutating the original and prevent fragmentation warnings
    df = fundamental_stock.copy()

    # ---- 1. Derived columns ----
    df['EPS'] = df['netIncome_x'] / df['commonStockSharesOutstanding']
    df['FCF'] = df['operatingCashflow'] - df['capitalExpenditures']
    df['FCFPS'] = df['FCF'] / df['commonStockSharesOutstanding']
    df['PE_Ratio'] = df['close'] / df['EPS']  # P/E ratio

    # ---- 2. Add year and select one row per fiscal year (first report) ----
    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    yearly = df.groupby('year').first().reset_index()

    # ---- 3. Compute Dividends per Share correctly ----
    # Check which total dividend column exists
    if 'dividendPayout' in yearly.columns:
        yearly['DividendsPerShare'] = yearly['dividendPayout'] / yearly['commonStockSharesOutstanding']
    elif 'dividendPayoutCommonStock' in yearly.columns:
        yearly['DividendsPerShare'] = yearly['dividendPayoutCommonStock'] / yearly['commonStockSharesOutstanding']
    else:
        # No dividend data available – we will still create the column with None
        yearly['DividendsPerShare'] = None

    # Metrics to include in growth table (English keys)
    metrics = {
        'Revenue': 'totalRevenue',
        'Net Income': 'netIncome_x',
        'EPS': 'EPS',
        'Dividends': 'DividendsPerShare'
    }

    # ---- 4. Pivot: years as columns, metrics as rows ----
    # Keep only year and the metric columns
    yearly_subset = yearly[['year'] + list(metrics.values())].set_index('year')
    pivoted = yearly_subset.T  # rows = metrics, columns = years

    # ---- 5. Calculate growth rates over 1, 3, 5, 8 years ----
    years_sorted = sorted(pivoted.columns)  # ascending, e.g. [2015, 2016, ..., 2025]
    if len(years_sorted) < 2:
        # Not enough data to compute any growth
        return pd.DataFrame()

    latest = years_sorted[-1]

    periods = {
        '1 Year': latest - 1,
        '3 Years': latest - 3,
        '5 Years': latest - 5,
        '8 Years': latest - 8
    }

    growth_df = pd.DataFrame(index=pivoted.index, columns=periods.keys())

    for metric in pivoted.index:
        for period_label, target_year in periods.items():
            if target_year in pivoted.columns and latest in pivoted.columns:
                old = pivoted.loc[metric, target_year]
                new = pivoted.loc[metric, latest]
                if pd.isna(old) or pd.isna(new):
                    pct = None
                elif old == 0:
                    pct = float('inf') if new > 0 else float('-inf') if new < 0 else 0.0
                else:
                    pct = (new - old) / abs(old) * 100.0
                growth_df.loc[metric, period_label] = pct
            else:
                growth_df.loc[metric, period_label] = None

    return growth_df.round(2)


def per_share_values(fundamental_stock):
    df = fundamental_stock.copy()

    # Basic derived values
    df['EPS'] = df['netIncome_x'] / df['commonStockSharesOutstanding']
    df['FCF'] = df['operatingCashflow'] - df['capitalExpenditures']

    # Per‑share metrics (English column names)
    df['Earnings Per Share'] = df['EPS']
    df['Free Cash Flow Per Share'] = df['FCF'] / df['commonStockSharesOutstanding']

    # Dividends Per Share: use total dividends paid (either column)
    if 'dividendPayout' in df.columns:
        total_div = df['dividendPayout']
    elif 'dividendPayoutCommonStock' in df.columns:
        total_div = df['dividendPayoutCommonStock']
    else:
        total_div = 0
    df['Dividends Per Share'] = total_div / df['commonStockSharesOutstanding']

    df['Shares Outstanding (M)'] = df['commonStockSharesOutstanding'] / 1_000_000
    df['Book Value Per Share'] = df['totalShareholderEquity'] / df['commonStockSharesOutstanding']
    df['Cash Flow Per Share'] = df['operatingCashflow'] / df['commonStockSharesOutstanding']
    df['Revenue Per Share'] = df['totalRevenue'] / df['commonStockSharesOutstanding']

    # Annual aggregation: first report per fiscal year
    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    first_per_year = df.groupby('year').first().reset_index()

    # Select last 5 years (or as needed)
    last5_years = sorted(first_per_year['year'].unique())[-5:]

    metrics = [
        'Earnings Per Share',
        'Dividends Per Share',
        'Shares Outstanding (M)',
        'Book Value Per Share',
        'Cash Flow Per Share',
        'Free Cash Flow Per Share',
        'Revenue Per Share'
    ]

    # Pivot: years as columns, metrics as rows
    wide_df = first_per_year[first_per_year['year'].isin(last5_years)].set_index('year')[metrics].T
    return wide_df.round(2)


def income_statement_overview(fundamental_stock):
    """
    Returns a DataFrame with:
        Operating Revenue,
        Operating Income,
        Interest Income (Expense),
        Income Before Tax,
        Income After Tax,
        Net Income
    in million USD, rows = metrics, columns = years (last 5 years).
    """
    df = fundamental_stock.copy()
    df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    yearly = df.groupby('year').first().reset_index()

    # Compute interest result
    if 'netInterestIncome' in yearly.columns and yearly['netInterestIncome'].notna().any():
        interest_result = yearly['netInterestIncome']
    elif 'interestIncome' in yearly.columns and 'interestExpense' in yearly.columns:
        interest_result = yearly['interestIncome'] - yearly['interestExpense']
    else:
        interest_result = None

    metrics = {}
    if 'totalRevenue' in yearly.columns:
        metrics['Operating Revenue'] = yearly['totalRevenue'] / 1_000_000
    if 'operatingIncome' in yearly.columns:
        metrics['Operating Income'] = yearly['operatingIncome'] / 1_000_000
    if interest_result is not None:
        metrics['Interest Income (Expense)'] = interest_result / 1_000_000
    if 'incomeBeforeTax' in yearly.columns:
        metrics['Income Before Tax'] = yearly['incomeBeforeTax'] / 1_000_000
    if 'netIncomeFromContinuingOperations' in yearly.columns:
        metrics['Income After Tax'] = yearly['netIncomeFromContinuingOperations'] / 1_000_000
    elif 'netIncome_x' in yearly.columns:
        metrics['Income After Tax'] = yearly['netIncome_x'] / 1_000_000
    if 'netIncome_x' in yearly.columns:
        metrics['Net Income'] = yearly['netIncome_x'] / 1_000_000
    elif 'netIncome' in yearly.columns:
        metrics['Net Income'] = yearly['netIncome'] / 1_000_000

    if not metrics:
        return pd.DataFrame()

    result = pd.DataFrame(metrics).T
    # Assign actual years as column names
    result.columns = yearly['year'].values
    # Keep only last 5 years (or fewer if not available)
    years_sorted = sorted(yearly['year'].unique())
    last5_years = years_sorted[-5:]
    result = result[[col for col in result.columns if col in last5_years]]
    return result.round(2)


def balance_sheet_overview(fundamental_stock):
    """
    Returns a DataFrame with:
        Cash,
        Total Assets,
        Long-Term Liabilities,
        Total Liabilities,
        Equity
    in million USD, rows = metrics, columns = years (last 5 years).
    """
    df = fundamental_stock.copy()
    df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    yearly = df.groupby('year').first().reset_index()

    # Ensure long-term liabilities exist
    if 'totalNonCurrentLiabilities' not in yearly.columns:
        if 'totalLiabilities' in yearly.columns and 'totalCurrentLiabilities' in yearly.columns:
            yearly['totalNonCurrentLiabilities'] = yearly['totalLiabilities'] - yearly['totalCurrentLiabilities']

    metrics = {}
    if 'cashAndCashEquivalentsAtCarryingValue' in yearly.columns:
        metrics['Cash'] = yearly['cashAndCashEquivalentsAtCarryingValue'] / 1_000_000
    if 'totalAssets' in yearly.columns:
        metrics['Total Assets'] = yearly['totalAssets'] / 1_000_000
    if 'totalNonCurrentLiabilities' in yearly.columns:
        metrics['Long-Term Liabilities'] = yearly['totalNonCurrentLiabilities'] / 1_000_000
    if 'totalLiabilities' in yearly.columns:
        metrics['Total Liabilities'] = yearly['totalLiabilities'] / 1_000_000
    if 'totalShareholderEquity' in yearly.columns:
        metrics['Equity'] = yearly['totalShareholderEquity'] / 1_000_000

    if not metrics:
        return pd.DataFrame()

    result = pd.DataFrame(metrics).T
    result.columns = yearly['year'].values
    years_sorted = sorted(yearly['year'].unique())
    last5_years = years_sorted[-5:]
    result = result[[col for col in result.columns if col in last5_years]]
    return result.round(2)


def cashflow_overview(fundamental_stock):
    """
    Returns a DataFrame with:
        Depreciation,
        Cash Flow from Operations,
        Capital Expenditures (Investment),
        Cash Flow from Investing,
        Cash Flow from Financing,
        Change in Cash
    in million USD, rows = metrics, columns = years (last 5 years).
    """
    df = fundamental_stock.copy()
    df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    yearly = df.groupby('year').first().reset_index()

    # Capital Expenditures = -capitalExpenditures (outflow negative)
    investment_spending = None
    if 'capitalExpenditures' in yearly.columns:
        investment_spending = -yearly['capitalExpenditures']

    metrics = {}
    if 'depreciationDepletionAndAmortization' in yearly.columns:
        metrics['Depreciation'] = yearly['depreciationDepletionAndAmortization'] / 1_000_000
    if 'operatingCashflow' in yearly.columns:
        metrics['Cash Flow from Operations'] = yearly['operatingCashflow'] / 1_000_000
    if investment_spending is not None:
        metrics['Capital Expenditures (Investment)'] = investment_spending / 1_000_000
    if 'cashflowFromInvestment' in yearly.columns:
        metrics['Cash Flow from Investing'] = yearly['cashflowFromInvestment'] / 1_000_000
    if 'cashflowFromFinancing' in yearly.columns:
        metrics['Cash Flow from Financing'] = yearly['cashflowFromFinancing'] / 1_000_000

    # Change in Cash
    if 'changeInCashAndCashEquivalents' in yearly.columns:
        metrics['Change in Cash'] = yearly['changeInCashAndCashEquivalents'] / 1_000_000
    elif 'cashAndCashEquivalentsAtCarryingValue' in yearly.columns:
        change = yearly['cashAndCashEquivalentsAtCarryingValue'].diff()
        metrics['Change in Cash'] = change / 1_000_000

    if not metrics:
        return pd.DataFrame()

    result = pd.DataFrame(metrics).T
    result.columns = yearly['year'].values
    years_sorted = sorted(yearly['year'].unique())
    last5_years = years_sorted[-5:]
    result = result[[col for col in result.columns if col in last5_years]]
    return result.round(2)