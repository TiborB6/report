import yfinance as yf
import numpy as np

def calculate_cost_of_equity(beta, rf, market_risk_premium):
    """CAPM: required return = risk‑free rate + beta * market risk premium"""
    return rf + beta * market_risk_premium

def compute_cagr(start_value, end_value, years):
    """Compound Annual Growth Rate"""
    if start_value <= 0 or years <= 0:
        return 0.03   # fallback
    return (end_value / start_value) ** (1 / years) - 1

def gordon_growth_value(current_dividend, required_return, growth_rate):
    """Gordon Growth Model (stable growth)"""
    if required_return <= growth_rate:
        growth_rate = required_return * 0.9
    next_dividend = current_dividend * (1 + growth_rate)
    return next_dividend / (required_return - growth_rate)

def ddm_calculation(ticker):
    rf = 0.04
    mrp = 0.046
    stock = yf.Ticker(ticker)

    info = stock.info
    beta = info.get('beta')
    if beta is None:
        beta = 1.0

    current_price = info.get('currentPrice', info.get('regularMarketPrice'))

    annual_dividend = info.get('dividendRate')
    if annual_dividend is None:
        dividends = stock.dividends
        if not dividends.empty:
            annual_dividend = dividends.tail(4).sum()
        else:
            annual_dividend = None

    if annual_dividend is None:
        raise ValueError("No dividend data available for JPM")

    required_return = calculate_cost_of_equity(beta, rf, mrp)

    dividends = stock.dividends
    if dividends.empty:
        growth_rate = 0.03
    else:
        div_series = dividends.to_frame('div')
        div_series['year'] = div_series.index.year
        annual_divs = div_series.groupby('year')['div'].sum()

        complete_years = annual_divs[annual_divs.index < 2026]
        if len(complete_years) >= 5:
            recent = complete_years.tail(5)
            start_value = recent.iloc[0]
            end_value = recent.iloc[-1]
            years = len(recent) - 1
            growth_rate = compute_cagr(start_value, end_value, years)
        elif len(complete_years) >= 2:
            growth_rates = complete_years.pct_change().dropna()
            growth_rate = growth_rates.mean()
        else:
            growth_rate = 0.03

        if np.isnan(growth_rate) or growth_rate < 0:
            growth_rate = 0.03
        if growth_rate >= required_return:
            growth_rate = required_return * 0.9

    target_price = gordon_growth_value(annual_dividend, required_return, growth_rate)

    print(f"Cost of Equity (CAPM): {required_return:.2%}")
    print(f"Sustainable growth rate (5‑yr CAGR): {growth_rate:.2%}")
    print(f"12‑Month DDM Target Price: ${target_price:.2f}")
    print(f"Current Price: ${current_price:.2f}")

    if target_price * 0.9 > current_price:
        evaluation = "BUY"
    elif target_price * 1.1 < current_price:
        evaluation = "SELL"
    else:
        evaluation = "HOLD"

    return evaluation