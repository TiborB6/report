import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

def estimate_dividend_structure(fundamental_df, overview_df, years=5):
    """
    Forecast dividends using ARIMA on annual EPS and historical payout ratio.
    """
    df = fundamental_df.copy()
    df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
    df = df.sort_values('fiscalDateEnding')
    df['eps_q'] = df['netIncome_x'] / df['commonStockSharesOutstanding']
    df['year'] = df['fiscalDateEnding'].dt.year

    annual = df.groupby('year').agg({
        'eps_q': 'sum',
        'dividendPayoutCommonStock': 'sum',
        'commonStockSharesOutstanding': 'first'
    }).reset_index()

    quarter_counts = df.groupby('year').size()
    complete_years = quarter_counts[quarter_counts >= 4].index
    annual = annual[annual['year'].isin(complete_years)]

    annual['dps'] = annual['dividendPayoutCommonStock'] / annual['commonStockSharesOutstanding']
    annual['payout_ratio'] = annual['dps'] / annual['eps_q']

    annual = annual.dropna(subset=['eps_q', 'payout_ratio'])
    annual = annual[annual['eps_q'] > 0]

    payout_ratio = annual['payout_ratio'].tail(8).median()
    eps_annual = annual['eps_q'].values

    model = ARIMA(eps_annual, order=(1, 1, 0))
    fitted = model.fit()
    eps_forecast = fitted.forecast(steps=years)

    last_dps = annual['dps'].iloc[-1]
    analyst_div = float(overview_df.get('DividendPerShare', last_dps))

    future_dividends = []
    for i, eps_f in enumerate(eps_forecast):
        if i == 0 and analyst_div > 0:
            div = analyst_div
        else:
            div = eps_f * payout_ratio
            div = max(div, 0)
        future_dividends.append(round(div, 4))

    return future_dividends


def dividend_discount_table(dividends, beta, rf=0.04, market_risk_premium=0.046,
                            terminal_growth=0.02, years=None):
    """
    Compute discounted dividends and target prices using CAPM discount rate.

    Parameters:
    - dividends: list or array of forecasted dividends per share for years 1..N
    - beta: company's beta (e.g., from Yahoo Finance)
    - rf: risk-free rate (default 0.04 = 4%)
    - market_risk_premium: E[rm]-rf (default 0.046 = 4.6%)
    - terminal_growth: constant growth rate after the last forecast year (e.g., 0.02 = 2%)
    - years: optional list of year numbers (default 1..len(dividends))

    Returns:
    - DataFrame with columns:
        Year | Dividend per Share | Discounted Dividend per Share | Target Price per Share
    """
    i = rf + beta * market_risk_premium

    N = len(dividends)
    if years is None:
        years = list(range(1, N + 1))

    d_next = dividends[-1] * (1 + terminal_growth)
    terminal_value = d_next / (i - terminal_growth)

    disc_factors = [1 / (1 + i) ** t for t in years]

    discounted_divs = [div * df for div, df in zip(dividends, disc_factors)]

    target_prices = []
    for t in range(1, N + 1):
        future_divs = dividends[t:]
        if not future_divs:
            price = terminal_value / (1 + i) ** (N - t)
        else:
            pv = 0
            for j, div in enumerate(future_divs):
                year_of_div = t + 1 + j
                pv += div / (1 + i) ** (year_of_div - t)
            pv += terminal_value / (1 + i) ** (N - t)
            price = pv
        target_prices.append(price)

    df = pd.DataFrame({
        'Year': years,
        'Dividend per Share': dividends,
        'Discounted Dividend per Share': [round(x, 4) for x in discounted_divs],
        'Target Price per Share': [round(p, 4) for p in target_prices]
    })

    return df

def get_ddm_valuation(fundamental_df, overview_df):
    dividends = estimate_dividend_structure(fundamental_df, overview_df)
    return dividend_discount_table(dividends, float(overview_df['Beta']))