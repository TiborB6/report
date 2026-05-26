import pandas as pd

def _escape_underscores(df):
    """Escape underscores in all string index and column labels of a DataFrame."""
    if df.empty:
        return df
    if df.index.dtype == 'object':
        df.index = [str(idx).replace('_', '\\_') for idx in df.index]
    if df.columns.dtype == 'object':
        df.columns = [str(col).replace('_', '\\_') for col in df.columns]
    return df

def _aggregate_annual(df):
    """
    Convert quarterly data to annual:
    - Flow items (income, cash flow) are summed.
    - Snapshot items (balance sheet, shares, price) are taken as the last value of the year.
    """
    df = df.copy()
    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')

    snapshot_cols = [
        'commonStockSharesOutstanding',
        'totalShareholderEquity', 'totalAssets', 'totalLiabilities',
        'cashAndCashEquivalentsAtCarryingValue',
        'close', 'open', 'high', 'low', 'volume'
    ]
    balance_sheet_keywords = ['Assets', 'Liabilities', 'Equity', 'Debt', 'Receivables', 'Payables']
    for col in df.columns:
        if any(kw in col for kw in balance_sheet_keywords):
            if col not in snapshot_cols:
                snapshot_cols.append(col)

    snapshot_cols_present = [c for c in snapshot_cols if c in df.columns]
    all_numeric = df.select_dtypes(include='number').columns.tolist()
    flow_cols = [c for c in all_numeric if c not in snapshot_cols_present and c != 'year']

    annual_list = []
    for year, group in df.groupby('year'):
        row = {'year': year}
        for col in flow_cols:
            row[col] = group[col].sum()
        for col in snapshot_cols_present:
            row[col] = group[col].iloc[-1]
        row['fiscalDateEnding'] = group['fiscalDateEnding'].iloc[-1]
        annual_list.append(row)

    annual_df = pd.DataFrame(annual_list)
    return annual_df

def key_figures(fundamental_stock, n=5):
    df = fundamental_stock.copy()
    df = _aggregate_annual(df)
    df['EPS'] = df['netIncome_x'] / df['commonStockSharesOutstanding']
    df['FCF'] = df['operatingCashflow'] - df['capitalExpenditures']
    df['FCFPS'] = df['FCF'] / df['commonStockSharesOutstanding']
    df['PE_Ratio'] = df['close'] / df['EPS']
    df = df.sort_values('year')
    last_n_years = sorted(df['year'].unique())[-n:]
    metrics = ['close', 'EPS', 'PE_Ratio', 'FCFPS']
    wide_df = df[df['year'].isin(last_n_years)].set_index('year')[metrics].T
    return _escape_underscores(wide_df.round(2))

def key_growth_rates(fundamental_stock):
    df = fundamental_stock.copy()
    df_annual = _aggregate_annual(df)

    quarter_counts = fundamental_stock.groupby(fundamental_stock['fiscalDateEnding'].dt.year)['fiscalDateEnding'].count()
    full_years = quarter_counts[quarter_counts == 4].index.tolist()
    df_annual = df_annual[df_annual['year'].isin(full_years)]

    if df_annual.empty:
        return pd.DataFrame()

    df_annual['EPS'] = df_annual['netIncome_x'] / df_annual['commonStockSharesOutstanding']
    df_annual['FCF'] = df_annual['operatingCashflow'] - df_annual['capitalExpenditures']
    df_annual['FCFPS'] = df_annual['FCF'] / df_annual['commonStockSharesOutstanding']
    df_annual['PE_Ratio'] = df_annual['close'] / df_annual['EPS']

    if 'dividendPayout' in df_annual.columns:
        df_annual['DividendsPerShare'] = df_annual['dividendPayout'] / df_annual['commonStockSharesOutstanding']
    elif 'dividendPayoutCommonStock' in df_annual.columns:
        df_annual['DividendsPerShare'] = df_annual['dividendPayoutCommonStock'] / df_annual['commonStockSharesOutstanding']
    else:
        df_annual['DividendsPerShare'] = None

    metrics = {
        'Revenue': 'totalRevenue',
        'Net Income': 'netIncome_x',
        'EPS': 'EPS',
        'Dividends': 'DividendsPerShare'
    }

    yearly_subset = df_annual[['year'] + list(metrics.values())].set_index('year')
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
    df = _aggregate_annual(df)

    df['Earnings Per Share'] = df['netIncome_x'] / df['commonStockSharesOutstanding']
    df['Free Cash Flow'] = df['operatingCashflow'] - df['capitalExpenditures']
    df['Free Cash Flow Per Share'] = df['Free Cash Flow'] / df['commonStockSharesOutstanding']

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

    last5_years = sorted(df['year'].unique())[-5:]

    metrics = [
        'Earnings Per Share',
        'Dividends Per Share',
        'Shares Outstanding (M)',
        'Book Value Per Share',
        'Cash Flow Per Share',
        'Free Cash Flow Per Share',
        'Revenue Per Share'
    ]

    wide_df = df[df['year'].isin(last5_years)].set_index('year')[metrics].T
    return _escape_underscores(wide_df.round(2))

def income_statement_overview(fundamental_stock):
    df = fundamental_stock.copy()
    df = _aggregate_annual(df)

    if 'netInterestIncome' in df.columns and df['netInterestIncome'].notna().any():
        interest_result = df['netInterestIncome']
    elif 'interestIncome' in df.columns and 'interestExpense' in df.columns:
        interest_result = df['interestIncome'] - df['interestExpense']
    else:
        interest_result = None

    metrics = {}
    if 'totalRevenue' in df.columns:
        metrics['Operating Revenue'] = df['totalRevenue'] / 1_000_000
    if 'operatingIncome' in df.columns:
        metrics['Operating Income'] = df['operatingIncome'] / 1_000_000
    if interest_result is not None:
        metrics['Interest Income (Expense)'] = interest_result / 1_000_000
    if 'incomeBeforeTax' in df.columns:
        metrics['Income Before Tax'] = df['incomeBeforeTax'] / 1_000_000
    if 'netIncomeFromContinuingOperations' in df.columns:
        metrics['Income After Tax'] = df['netIncomeFromContinuingOperations'] / 1_000_000
    elif 'netIncome_x' in df.columns:
        metrics['Income After Tax'] = df['netIncome_x'] / 1_000_000
    if 'netIncome_x' in df.columns:
        metrics['Net Income'] = df['netIncome_x'] / 1_000_000
    elif 'netIncome' in df.columns:
        metrics['Net Income'] = df['netIncome'] / 1_000_000

    if not metrics:
        return pd.DataFrame()

    result = pd.DataFrame(metrics).T
    result.columns = df['year'].values
    years_sorted = sorted(df['year'].unique())
    last5_years = years_sorted[-5:]
    result = result[[col for col in result.columns if col in last5_years]]
    return _escape_underscores(result.round(2))

def balance_sheet_overview(fundamental_stock):
    df = fundamental_stock.copy()
    df = _aggregate_annual(df)

    if 'totalNonCurrentLiabilities' not in df.columns:
        if 'totalLiabilities' in df.columns and 'totalCurrentLiabilities' in df.columns:
            df['totalNonCurrentLiabilities'] = df['totalLiabilities'] - df['totalCurrentLiabilities']

    metrics = {}
    if 'cashAndCashEquivalentsAtCarryingValue' in df.columns:
        metrics['Cash'] = df['cashAndCashEquivalentsAtCarryingValue'] / 1_000_000
    if 'totalAssets' in df.columns:
        metrics['Total Assets'] = df['totalAssets'] / 1_000_000
    if 'totalNonCurrentLiabilities' in df.columns:
        metrics['Long-Term Liabilities'] = df['totalNonCurrentLiabilities'] / 1_000_000
    if 'totalLiabilities' in df.columns:
        metrics['Total Liabilities'] = df['totalLiabilities'] / 1_000_000
    if 'totalShareholderEquity' in df.columns:
        metrics['Equity'] = df['totalShareholderEquity'] / 1_000_000

    if not metrics:
        return pd.DataFrame()

    result = pd.DataFrame(metrics).T
    result.columns = df['year'].values
    years_sorted = sorted(df['year'].unique())
    last5_years = years_sorted[-5:]
    result = result[[col for col in result.columns if col in last5_years]]
    return _escape_underscores(result.round(2))

def cashflow_overview(fundamental_stock):
    df = fundamental_stock.copy()
    df = _aggregate_annual(df)

    dep = df['depreciationDepletionAndAmortization'].abs()
    capx = -df['capitalExpenditures'].abs()

    metrics = {
        'Depreciation': dep / 1_000_000,
        'Cash Flow from Operations': df['operatingCashflow'] / 1_000_000,
        'Capital Expenditures (Investment)': capx / 1_000_000,
        'Cash Flow from Investing': df['cashflowFromInvestment'] / 1_000_000,
        'Cash Flow from Financing': df['cashflowFromFinancing'] / 1_000_000,
    }

    df = df.sort_values('year')
    df['cash_change'] = df['cashAndCashEquivalentsAtCarryingValue'].diff()
    metrics['Change in Cash'] = df['cash_change'] / 1_000_000

    result = pd.DataFrame(metrics).T
    result.columns = df['year'].values
    last5_years = sorted(result.columns)[-5:]
    result = result[last5_years]
    return _escape_underscores(result.round(2))