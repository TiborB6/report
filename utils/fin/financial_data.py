import pandas as pd

def key_figures(fundamental_stock):
    df = fundamental_stock.copy()   # work on a copy
    df['EPS'] = df['netIncome_x'] / df['commonStockSharesOutstanding']
    df['FCF'] = df['operatingCashflow'] - df['capitalExpenditures']
    df['FCFPS'] = df['FCF'] / df['commonStockSharesOutstanding']
    df['KGV'] = df['close'] / df['EPS']
    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    first_per_year = df.groupby('year').first().reset_index()
    last5_years = sorted(first_per_year['year'].unique())[-5:]
    metrics = ['close', 'EPS', 'KGV', 'FCFPS']
    wide_df = first_per_year[first_per_year['year'].isin(last5_years)].set_index('year')[metrics].T
    return wide_df


def key_growth_rates(fundamental_stock):
    # Work on a copy to avoid mutating the original and prevent fragmentation warnings
    df = fundamental_stock.copy()

    # ---- 1. Derived columns ----
    df['EPS'] = df['netIncome_x'] / df['commonStockSharesOutstanding']
    df['FCF'] = df['operatingCashflow'] - df['capitalExpenditures']
    df['FCFPS'] = df['FCF'] / df['commonStockSharesOutstanding']
    df['KGV'] = df['close'] / df['EPS']  # P/E ratio

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

    # Metrics to include in growth table
    metrics = {
        'Konzernumsatz': 'totalRevenue',
        'Konzernergebnis': 'netIncome_x',
        'Gewinn je Aktie': 'EPS',
        'Dividenden': 'DividendsPerShare'
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
        '1 Jahr': latest - 1,
        '3 Jahren': latest - 3,
        '5 Jahren': latest - 5,
        '8 Jahren': latest - 8
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

    return growth_df


def per_share_values(fundamental_stock):
    df = fundamental_stock.copy()

    # Basic derived values
    df['EPS'] = df['netIncome_x'] / df['commonStockSharesOutstanding']
    df['FCF'] = df['operatingCashflow'] - df['capitalExpenditures']

    # Per‑share metrics
    df['Gewinn je Aktie'] = df['EPS']
    df['Free Cashflow je Aktie'] = df['FCF'] / df['commonStockSharesOutstanding']

    # Dividende je Aktie: use total dividends paid (either column)
    if 'dividendPayout' in df.columns:
        total_div = df['dividendPayout']
    elif 'dividendPayoutCommonStock' in df.columns:
        total_div = df['dividendPayoutCommonStock']
    else:
        total_div = 0
    df['Dividende je Aktie'] = total_div / df['commonStockSharesOutstanding']

    df['Ausstehende Aktien (Mio)'] = df['commonStockSharesOutstanding'] / 1_000_000
    df['Buchwert je Aktie'] = df['totalShareholderEquity'] / df['commonStockSharesOutstanding']
    df['Cashflow je Aktie'] = df['operatingCashflow'] / df['commonStockSharesOutstanding']
    df['Konzernumsatz je Aktie'] = df['totalRevenue'] / df['commonStockSharesOutstanding']

    # Annual aggregation: first report per fiscal year
    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    first_per_year = df.groupby('year').first().reset_index()

    # Select last 5 years (or as needed)
    last5_years = sorted(first_per_year['year'].unique())[-5:]

    metrics = [
        'Gewinn je Aktie',
        'Dividende je Aktie',
        'Ausstehende Aktien (Mio)',
        'Buchwert je Aktie',
        'Cashflow je Aktie',
        'Free Cashflow je Aktie',
        'Konzernumsatz je Aktie'
    ]

    # Pivot: years as columns, metrics as rows
    wide_df = first_per_year[first_per_year['year'].isin(last5_years)].set_index('year')[metrics].T
    return wide_df


def income_statement_overview(fundamental_stock):
    """
    Returns a DataFrame with:
        Operativer Konzernumsatz,
        Operatives Betriebsergebnis,
        Zinserträge (-aufwände),
        Ergebnis vor Steuern,
        Ergebnis nach Steuern,
        Konzernergebnis
    in million USD, rows = metrics, columns = years (last 5 years).
    """
    df = fundamental_stock.copy()

    # Annual aggregation (first report per fiscal year)
    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    yearly = df.groupby('year').first().reset_index()

    # Compute interest result (if netInterestIncome not available, use interestIncome - interestExpense)
    if 'netInterestIncome' in yearly.columns and yearly['netInterestIncome'].notna().any():
        interest_result = yearly['netInterestIncome']
    elif 'interestIncome' in yearly.columns and 'interestExpense' in yearly.columns:
        interest_result = yearly['interestIncome'] - yearly['interestExpense']
    else:
        interest_result = None

    # Define metrics and their source columns (values in millions, so divide by 1e6 if needed)
    # Note: All source columns are already in dollars, so we convert to millions.
    metrics = {
        'Operativer Konzernumsatz': yearly['totalRevenue'] / 1_000_000,
        'Operatives Betriebsergebnis': yearly['operatingIncome'] / 1_000_000,
        'Zinserträge (-aufwände)': interest_result / 1_000_000 if interest_result is not None else None,
        'Ergebnis vor Steuern': yearly['incomeBeforeTax'] / 1_000_000,
        'Ergebnis nach Steuern': yearly.get('netIncomeFromContinuingOperations', yearly['netIncome_x']) / 1_000_000,
        'Konzernergebnis': yearly['netIncome_x'] / 1_000_000
    }

    # Build DataFrame: rows = metrics, columns = years
    result = pd.DataFrame({name: series for name, series in metrics.items() if series is not None}).T
    # Keep only last 5 years
    years_sorted = sorted(yearly['year'].unique())
    last5_years = years_sorted[-5:]
    result = result[[col for col in result.columns if col in last5_years]]
    return result


def balance_sheet_overview(fundamental_stock):
    """
    Returns a DataFrame with:
        Barmittel,
        Summe Aktiva,
        Langfristige Verbindlichkeiten,
        Summe Passiva,
        Eigenkapital
    in million USD, rows = metrics, columns = years (last 5 years).
    """
    df = fundamental_stock.copy()

    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    yearly = df.groupby('year').first().reset_index()

    # Use totalNonCurrentLiabilities for "Langfristige Verbindlichkeiten" (long‑term liabilities)
    if 'totalNonCurrentLiabilities' not in yearly.columns:
        # Fallback: totalLiabilities - totalCurrentLiabilities
        yearly['totalNonCurrentLiabilities'] = yearly['totalLiabilities'] - yearly['totalCurrentLiabilities']

    metrics = {
        'Barmittel': yearly['cashAndCashEquivalentsAtCarryingValue'] / 1_000_000,
        'Summe Aktiva': yearly['totalAssets'] / 1_000_000,
        'Langfristige Verbindlichkeiten': yearly['totalNonCurrentLiabilities'] / 1_000_000,
        'Summe Passiva': yearly['totalLiabilities'] / 1_000_000,
        'Eigenkapital': yearly['totalShareholderEquity'] / 1_000_000
    }

    result = pd.DataFrame(metrics).T
    years_sorted = sorted(yearly['year'].unique())
    last5_years = years_sorted[-5:]
    result = result[[col for col in result.columns if col in last5_years]]
    return result


def cashflow_overview(fundamental_stock):
    """
    Returns a DataFrame with:
        Abschreibungen,
        CF Betriebliche Tätigkeit,
        Investitionsaufwand,
        CF Investitionstätigkeit,
        CF Finanzierungstätigkeit,
        Veränderung flüssige Mittel
    in million USD, rows = metrics, columns = years (last 5 years).
    """
    df = fundamental_stock.copy()

    df['year'] = df['fiscalDateEnding'].dt.year
    df = df.sort_values('fiscalDateEnding')
    yearly = df.groupby('year').first().reset_index()

    # Investitionsaufwand is typically negative (cash outflow). We use -capitalExpenditures to match the sample.
    # If capitalExpenditures is already negative, adjust accordingly.
    # In your data, capitalExpenditures is likely positive (outlay), so we take negative.
    investment_spending = -yearly['capitalExpenditures'] if 'capitalExpenditures' in yearly.columns else None

    metrics = {
        'Abschreibungen': yearly['depreciationDepletionAndAmortization'] / 1_000_000,
        'CF Betriebliche Tätigkeit': yearly['operatingCashflow'] / 1_000_000,
        'Investitionsaufwand': investment_spending / 1_000_000 if investment_spending is not None else None,
        'CF Investitionstätigkeit': yearly['cashflowFromInvestment'] / 1_000_000,
        'CF Finanzierungstätigkeit': yearly['cashflowFromFinancing'] / 1_000_000,
        'Veränderung flüssige Mittel': yearly.get('changeInCashAndCashEquivalents',
                                                  yearly['cashAndCashEquivalentsAtCarryingValue'].diff()) / 1_000_000
    }

    # Remove any metric that could not be computed
    result = pd.DataFrame({name: series for name, series in metrics.items() if series is not None}).T
    years_sorted = sorted(yearly['year'].unique())
    last5_years = years_sorted[-5:]
    result = result[[col for col in result.columns if col in last5_years]]
    return result