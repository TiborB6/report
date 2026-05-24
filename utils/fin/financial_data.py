import pandas as pd

def _escape_underscores(df):
    """Escape underscores in all string index and column labels of a DataFrame."""
    if df.empty:
        return df
    # Escape index
    if df.index.dtype == 'object':
        df.index = [str(idx).replace('_', '\\_') for idx in df.index]
    # Escape columns
    if df.columns.dtype == 'object':
        df.columns = [str(col).replace('_', '\\_') for col in df.columns]
    return df


def key_figures(fundamental_stock, n=5):
    df = fundamental_stock.copy()
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
    return _escape_underscores(wide_df.round(2))


def key_growth_rates(fundamental_stock):
    df = fundamental_stock.copy()

    df['EPS'] = df['netIncome_x'] / df['commonStockSharesOutstanding']
    df['FCF'] = df['operatingCashflow'] - df['capitalExpenditures']
    df['FCFPS'] = df['FCF'] / df['commonStockSharesOutstanding']
    df['PE_Ratio'] = df['close'] / df['EPS']

    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    yearly = df.groupby('year').first().reset_index()

    if 'dividendPayout' in yearly.columns:
        yearly['DividendsPerShare'] = yearly['dividendPayout'] / yearly['commonStockSharesOutstanding']
    elif 'dividendPayoutCommonStock' in yearly.columns:
        yearly['DividendsPerShare'] = yearly['dividendPayoutCommonStock'] / yearly['commonStockSharesOutstanding']
    else:
        yearly['DividendsPerShare'] = None

    metrics = {
        'Revenue': 'totalRevenue',
        'Net Income': 'netIncome_x',
        'EPS': 'EPS',
        'Dividends': 'DividendsPerShare'
    }

    yearly_subset = yearly[['year'] + list(metrics.values())].set_index('year')
    pivoted = yearly_subset.T

    years_sorted = sorted(pivoted.columns)
    if len(years_sorted) < 2:
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

    return _escape_underscores(growth_df.round(2))


def per_share_values(fundamental_stock):
    df = fundamental_stock.copy()

    df['EPS'] = df['netIncome_x'] / df['commonStockSharesOutstanding']
    df['FCF'] = df['operatingCashflow'] - df['capitalExpenditures']

    df['Earnings Per Share'] = df['EPS']
    df['Free Cash Flow Per Share'] = df['FCF'] / df['commonStockSharesOutstanding']

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

    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    first_per_year = df.groupby('year').first().reset_index()

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

    wide_df = first_per_year[first_per_year['year'].isin(last5_years)].set_index('year')[metrics].T
    return _escape_underscores(wide_df.round(2))


def income_statement_overview(fundamental_stock):
    df = fundamental_stock.copy()
    df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    yearly = df.groupby('year').first().reset_index()

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
    result.columns = yearly['year'].values
    years_sorted = sorted(yearly['year'].unique())
    last5_years = years_sorted[-5:]
    result = result[[col for col in result.columns if col in last5_years]]
    return _escape_underscores(result.round(2))


def balance_sheet_overview(fundamental_stock):
    df = fundamental_stock.copy()
    df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    yearly = df.groupby('year').first().reset_index()

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
    return _escape_underscores(result.round(2))


def cashflow_overview(fundamental_stock):
    df = fundamental_stock.copy()
    df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
    df = df.sort_values('fiscalDateEnding')
    # Take the last (most recent) report per calendar year – works for YTD quarterly data
    yearly = df.groupby(df['fiscalDateEnding'].dt.year).last().reset_index(drop=True)

    # Fix sign for depreciation
    dep = yearly['depreciationDepletionAndAmortization'].abs()
    # Cash Flow from Investing often already includes CapEx; keep separate only if you need breakdown
    capx = -yearly['capitalExpenditures'].abs()  # negative outflow

    metrics = {
        'Depreciation': dep / 1_000_000,
        'Cash Flow from Operations': yearly['operatingCashflow'] / 1_000_000,
        'Capital Expenditures (Investment)': capx / 1_000_000,
        'Cash Flow from Investing': yearly['cashflowFromInvestment'] / 1_000_000,
        'Cash Flow from Financing': yearly['cashflowFromFinancing'] / 1_000_000,
    }

    # Compute change in cash from balance sheet
    yearly['cash_change'] = yearly['cashAndCashEquivalentsAtCarryingValue'].diff()
    metrics['Change in Cash'] = yearly['cash_change'] / 1_000_000

    result = pd.DataFrame(metrics).T
    result.columns = yearly['fiscalDateEnding'].dt.year
    last5_years = sorted(result.columns)[-5:]
    result = result[last5_years]
    return _escape_underscores(result.round(2))