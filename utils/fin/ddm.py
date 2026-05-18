import yfinance as yf
import numpy as np
from typing import Dict, Union, Optional
import pandas as pd


def calculate_cost_of_equity(beta: float, rf: float, market_risk_premium: float) -> float:
    """CAPM: required return = risk‑free rate + beta * market risk premium"""
    return rf + beta * market_risk_premium


def compute_cagr(start_value: float, end_value: float, years: float) -> float:
    """Compound Annual Growth Rate"""
    if start_value <= 0 or years <= 0:
        return 0.03  # fallback
    return (end_value / start_value) ** (1 / years) - 1


def gordon_growth_value(current_dividend: float, required_return: float, growth_rate: float) -> float:
    """Gordon Growth Model (stable growth)"""
    if required_return <= growth_rate:
        growth_rate = required_return * 0.9  # safety cap
    next_dividend = current_dividend * (1 + growth_rate)
    return next_dividend / (required_return - growth_rate)


def get_ddm_valuation(ticker: str,
                      rf: float = 0.04,
                      mrp: float = 0.046) -> Dict[str, Union[float, str, None]]:
    """
    Perform Dividend Discount Model (DDM) valuation using Gordon Growth.

    Parameters:
    -----------
    ticker : str
        Stock ticker symbol (e.g., 'JPM')
    rf : float
        Risk‑free rate (default 4%)
    mrp : float
        Market risk premium (default 4.6%)

    Returns:
    --------
    dict containing:
        - target_price : fair value from DDM
        - current_price : latest market price
        - required_return : cost of equity (CAPM)
        - growth_rate : implied sustainable dividend growth rate
        - annual_dividend : trailing annual dividend per share
        - beta : stock's beta
        - risk_free_rate
        - market_risk_premium
        - evaluation : 'BUY' / 'HOLD' / 'SELL' (or None if price missing)
        - error : error message if any
    """
    result = {
        'target_price': None,
        'current_price': None,
        'required_return': None,
        'growth_rate': None,
        'annual_dividend': None,
        'beta': None,
        'risk_free_rate': rf,
        'market_risk_premium': mrp,
        'evaluation': None,
        'error': None
    }

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # --- Beta ---
        beta = info.get('beta')
        if beta is None:
            beta = 1.0
        result['beta'] = beta

        # --- Current price ---
        current_price = info.get('currentPrice', info.get('regularMarketPrice'))
        result['current_price'] = current_price

        # --- Annual dividend ---
        annual_dividend = info.get('dividendRate')
        if annual_dividend is None:
            dividends = stock.dividends
            if not dividends.empty:
                annual_dividend = dividends.tail(4).sum()  # last 4 quarters
            else:
                annual_dividend = None
        if annual_dividend is None or annual_dividend <= 0:
            raise ValueError(f"No positive dividend data available for {ticker}")
        result['annual_dividend'] = annual_dividend

        # --- Required return (CAPM) ---
        required_return = calculate_cost_of_equity(beta, rf, mrp)
        result['required_return'] = required_return

        # --- Estimate dividend growth rate ---
        dividends = stock.dividends
        if dividends.empty:
            growth_rate = 0.03
        else:
            div_series = dividends.to_frame('div')
            div_series['year'] = div_series.index.year
            annual_divs = div_series.groupby('year')['div'].sum()

            complete_years = annual_divs[annual_divs.index < 2026]  # avoid current incomplete year
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

        # Sanity checks
        if np.isnan(growth_rate) or growth_rate < 0.0:
            growth_rate = 0.03
        if growth_rate >= required_return:
            growth_rate = required_return * 0.9
        result['growth_rate'] = growth_rate

        # --- Target price via Gordon Growth ---
        target_price = gordon_growth_value(annual_dividend, required_return, growth_rate)
        result['target_price'] = target_price

        # --- Evaluation (if current price is available) ---
        if current_price is not None and current_price > 0:
            if target_price * 0.9 > current_price:
                result['evaluation'] = "BUY"
            elif target_price * 1.1 < current_price:
                result['evaluation'] = "SELL"
            else:
                result['evaluation'] = "HOLD"
        else:
            result['evaluation'] = None

    except Exception as e:
        result['error'] = str(e)

    return result


def get_ddm_table(ticker: str, forecast_years: int = 4,
                  rf: float = 0.04, mrp: float = 0.046):
    """
    Build a DDM table with forecast years as columns and two rows:
    - Dividende/Aktie
    - Diskontierte Dividende/Aktie
    Returns (DataFrame, terminal_value).
    """
    val = get_ddm_valuation(ticker, rf, mrp)
    if val['error']:
        raise ValueError(f"DDM error: {val['error']}")

    D0 = val['annual_dividend']
    r = val['required_return']
    g = val['growth_rate']
    current_price = val['current_price']  # not used in table but kept for context

    # 1. Forecast explicit dividends: D1..D_forecast_years
    dividends = [D0 * (1 + g) ** t for t in range(1, forecast_years + 1)]

    # 2. Discounted dividends
    discounted_divs = [div / (1 + r) ** t for t, div in enumerate(dividends, start=1)]

    # 3. Terminal value (Gordon Growth) – returned separately, not in table
    last_div = dividends[-1]
    terminal_value = last_div * (1 + g) / (r - g)

    # 4. Build DataFrame: columns = years, rows = metrics
    years = list(range(1, forecast_years + 1))
    df = pd.DataFrame({
        'Dividende/Aktie': dividends,
        'Diskontierte Dividende/Aktie': discounted_divs,
    }, index=years).T   # transpose so years become columns, metrics become rows

    return df, terminal_value