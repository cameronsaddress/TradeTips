import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# API key for Financial Modeling Prep (FMP)
# It is stored securely in Streamlit's secrets management.
# To set this up, create a file named `.streamlit/secrets.toml`
# and add `fmp_api_key = "YOUR_FMP_API_KEY"`
FMP_API_KEY = st.secrets["fmp_api_key"]

# FMP API base URL
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

def get_stock_data(symbol):
    """
    Fetches required financial data for a given stock from the FMP API.
    Returns a dictionary of metrics.
    """
    metrics = {
        'GPM': None,
        'ROIC': None,
        'Revenue_Growth': None,
        'EPS_Consistency': None,
        'Forward_PE': None,
        'CCC': None,
        'error': None
    }

    try:
        # --- Fetching GPM and ROIC from Financial Ratios endpoint ---
        ratios_url = f"{FMP_BASE_URL}/ratios/{symbol}?period=quarter&limit=1&apikey={FMP_API_KEY}"
        ratios_data = requests.get(ratios_url).json()
        if ratios_data and isinstance(ratios_data, list) and ratios_data[0]:
            metrics['GPM'] = ratios_data[0].get('grossProfitMargin')
            metrics['ROIC'] = ratios_data[0].get('roic')
        
        # --- Fetching Revenue Growth from Income Statement endpoint ---
        income_url = f"{FMP_BASE_URL}/income-statement/{symbol}?period=quarter&limit=5&apikey={FMP_API_KEY}"
        income_data = requests.get(income_url).json()
        if income_data and len(income_data) >= 4:
            current_revenue = income_data[0].get('revenue')
            year_ago_revenue = income_data[3].get('revenue')
            if year_ago_revenue and year_ago_revenue > 0:
                metrics['Revenue_Growth'] = (current_revenue - year_ago_revenue) / year_ago_revenue

        # --- Fetching EPS Consistency from Earnings Surprises endpoint ---
        earnings_url = f"{FMP_BASE_URL}/earnings-surprises/{symbol}?limit=4&apikey={FMP_API_KEY}"
        earnings_data = requests.get(earnings_url).json()
        if earnings_data and len(earnings_data) >= 4:
            # Check if actual EPS is greater than or equal to estimated EPS for the last 4 quarters
            all_beat = all(
                surprise.get('actualEarningResult') >= surprise.get('estimatedEarning')
                for surprise in earnings_data
            )
            metrics['EPS_Consistency'] = all_beat
            
        # --- Fetching Forward PE from Stock Quote endpoint ---
        quote_url = f"{FMP_BASE_URL}/quote/{symbol}?apikey={FMP_API_KEY}"
        quote_data = requests.get(quote_url).json()
        if quote_data and quote_data[0]:
            # FMP's quote endpoint provides a PE ratio, which can be forward-looking.
            metrics['Forward_PE'] = quote_data[0].get('pe')
            
        # --- Calculating CCC from Balance Sheet and Income Statement ---
        # We need data from the balance sheet (inventory, receivables, payables) and income statement (revenue, COGS)
        balance_sheet_url = f"{FMP_BASE_URL}/balance-sheet-statement/{symbol}?period=quarter&limit=2&apikey={FMP_API_KEY}"
        balance_sheet_data = requests.get(balance_sheet_url).json()

        income_statement_url = f"{FMP_BASE_URL}/income-statement/{symbol}?period=quarter&limit=2&apikey={FMP_API_KEY}"
        income_statement_data = requests.get(income_statement_url).json()

        if balance_sheet_data and balance_sheet_data[0] and income_statement_data and income_statement_data[0]:
            bs_latest = balance_sheet_data[0]
            inc_latest = income_statement_data[0]

            # Use trailing twelve months (TTM) where possible, or latest quarter annualized.
            cogs_ttm = inc_latest.get('costOfRevenue') * 4 # Annualizing Qtr COGS for TTM approx
            revenue_ttm = inc_latest.get('revenue') * 4 # Annualizing Qtr Revenue for TTM approx
            
            # Inventory, Receivables, Payables are from the Balance Sheet
            inventory = bs_latest.get('inventory')
            receivables = bs_latest.get('receivables')
            payables = bs_latest.get('accountPayables')
            
            # Days Inventory Outstanding (DIO)
            dio = (inventory / cogs_ttm) * 365 if cogs_ttm else None
            # Days Sales Outstanding (DSO)
            dso = (receivables / revenue_ttm) * 365 if revenue_ttm else None
            # Days Payable Outstanding (DPO)
            dpo = (payables / cogs_ttm) * 365 if cogs_ttm else None
            
            if dio is not None and dso is not None and dpo is not None:
                metrics['CCC'] = dio + dso - dpo

    except Exception as e:
        metrics['error'] = f"An error occurred while fetching data for {symbol}: {e}"

    return metrics

def get_ips_grade(metrics):
    """
    Grades a stock based on the IPS criteria using a simple scoring system.
    Returns the grade and a dictionary of reasons.
    """
    score = 0
    reasons = {}

    # GPM > 40% (high gross profit margin)
    if metrics['GPM'] is not None and metrics['GPM'] > 0.40:
        score += 1
        reasons['GPM'] = "✅ GPM > 40%"
    else:
        reasons['GPM'] = f"❌ GPM <= 40%" if metrics['GPM'] is not None else "⚠️ GPM data not found"

    # ROIC > 10% (high return on invested capital)
    if metrics['ROIC'] is not None and metrics['ROIC'] > 0.10:
        score += 1
        reasons['ROIC'] = "✅ ROIC > 10%"
    else:
        reasons['ROIC'] = f"❌ ROIC <= 10%" if metrics['ROIC'] is not None else "⚠️ ROIC data not found"

    # Revenue Growth > 10% (strong top-line growth)
    if metrics['Revenue_Growth'] is not None and metrics['Revenue_Growth'] > 0.10:
        score += 1
        reasons['Revenue_Growth'] = "✅ Revenue Growth > 10%"
    else:
        reasons['Revenue_Growth'] = f"❌ Revenue Growth <= 10%" if metrics['Revenue_Growth'] is not None else "⚠️ Revenue Growth data not found"

    # EPS Consistency (beat last 4 quarters' estimates)
    if metrics['EPS_Consistency'] is not None and metrics['EPS_Consistency'] is True:
        score += 1
        reasons['EPS_Consistency'] = "✅ Consistent EPS beats"
    else:
        reasons['EPS_Consistency'] = "❌ Did not consistently beat EPS estimates" if metrics['EPS_Consistency'] is not None else "⚠️ EPS consistency data not found"

    # Forward PE < 20 (attractive valuation)
    if metrics['Forward_PE'] is not None and metrics['Forward_PE'] < 20:
        score += 1
        reasons['Forward_PE'] = "✅ Forward PE < 20"
    else:
        reasons['Forward_PE'] = f"❌ Forward PE >= 20" if metrics['Forward_PE'] is not None else "⚠️ Forward PE data not found"

    # CCC < 30 days (efficient cash conversion cycle)
    if metrics['CCC'] is not None and metrics['CCC'] < 30:
        score += 1
        reasons['CCC'] = "✅ CCC < 30 days"
    else:
        reasons['CCC'] = f"❌ CCC >= 30 days" if metrics['CCC'] is not None else "⚠️ CCC data not found"

    # Assign a grade based on the score
    if score >= 5:
        grade = "A (Strong Buy)"
    elif score >= 3:
        grade = "B (Consider Buy)"
    elif score >= 1:
        grade = "C (Hold)"
    else:
        grade = "D (Sell)"
    
    return grade, reasons, score


def main():
    st.set_page_config(page_title="IPS Stock Screener", layout="wide")

    # Custom CSS for a better look and feel
    st.markdown("""
        <style>
        .main-header {
            font-size: 3rem;
            font-weight: bold;
            color: #4CAF50;
            text-align: center;
            margin-bottom: 0.5em;
        }
        .subheader {
            font-size: 1.5rem;
            color: #555;
            text-align: center;
            margin-bottom: 2em;
        }
        .st-emotion-cache-18ni7ap {
            padding: 1rem 1rem 1rem 1rem;
        }
        .st-emotion-cache-1avcm0s {
            background-color: #f0f2f6;
        }
        .metric-card {
            background-color: #f9f9f9;
            padding: 1em;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin-bottom: 1em;
        }
        .grade-card {
            text-align: center;
            font-size: 2em;
            font-weight: bold;
            padding: 1em;
            border-radius: 15px;
            color: white;
            margin-top: 1em;
        }
        .grade-A { background-color: #4CAF50; }
        .grade-B { background-color: #FFC107; }
        .grade-C { background-color: #2196F3; }
        .grade-D { background-color: #F44336; }
        .stButton button {
            background-color: #4CAF50;
            color: white;
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: bold;
            border: none;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header and description
    st.markdown('<div class="main-header">IPS Stock Screener</div>', unsafe_allow_html=True)
    st.markdown('<div class="subheader">Grade stocks based on the IPS financial framework</div>', unsafe_allow_html=True)

    # Sidebar for IPS explanation
    st.sidebar.header("What is IPS?")
    st.sidebar.markdown("""
    The **Investment Philosophy Score (IPS)** is a framework to evaluate stocks based on a set of fundamental metrics.
    
    A stock receives a point for each of the following criteria it meets:
    
    1.  **GPM > 40%**: Gross Profit Margin (GPM) is above 40%.
    2.  **ROIC > 10%**: Return on Invested Capital (ROIC) is above 10%.
    3.  **Revenue Growth > 10%**: Year-over-year revenue growth is above 10%.
    4.  **EPS Consistency**: Earnings per share (EPS) have consistently beaten estimates for the last four quarters.
    5.  **Forward PE < 20**: The stock's forward price-to-earnings (PE) ratio is below 20.
    6.  **CCC < 30 days**: Cash Conversion Cycle (CCC) is less than 30 days.
    
    Based on the total score, a grade is assigned:
    * **A**: 5-6 points (Strong Buy)
    * **B**: 3-4 points (Consider Buy)
    * **C**: 1-2 points (Hold)
    * **D**: 0 points (Sell)
    """)

    # Main input form
    with st.form("stock_form"):
        ticker = st.text_input("Enter a stock ticker (e.g., AAPL)", value="AAPL").upper()
        submit_button = st.form_submit_button("Analyze Stock")

    if submit_button:
        with st.spinner("Fetching and analyzing data..."):
            stock_metrics = get_stock_data(ticker)

        if stock_metrics.get('error'):
            st.error(stock_metrics['error'])
        else:
            grade, reasons, score = get_ips_grade(stock_metrics)
            
            st.markdown(f"### Results for {ticker}")
            
            # Display grade
            grade_color_class = f"grade-{grade.split()[0]}"
            st.markdown(f'<div class="grade-card {grade_color_class}">{grade}</div>', unsafe_allow_html=True)

            # Display a detailed table of metrics and reasons
            st.markdown("### IPS Criteria Breakdown")
            
            # Create a DataFrame for display
            df = pd.DataFrame({
                'Metric': ['GPM', 'ROIC', 'Revenue Growth', 'EPS Consistency', 'Forward PE', 'CCC'],
                'Criteria': ['> 40%', '> 10%', '> 10%', 'Beat estimates (last 4 qtrs)', '< 20', '< 30 days'],
                'Result': [
                    f"{stock_metrics['GPM']:.2%}" if stock_metrics['GPM'] is not None else "N/A",
                    f"{stock_metrics['ROIC']:.2%}" if stock_metrics['ROIC'] is not None else "N/A",
                    f"{stock_metrics['Revenue_Growth']:.2%}" if stock_metrics['Revenue_Growth'] is not None else "N/A",
                    "Yes" if stock_metrics['EPS_Consistency'] else "No",
                    f"{stock_metrics['Forward_PE']:.2f}" if stock_metrics['Forward_PE'] is not None else "N/A",
                    f"{stock_metrics['CCC']:.2f} days" if stock_metrics['CCC'] is not None else "N/A",
                ],
                'Meets Criteria': [reasons[k] for k in ['GPM', 'ROIC', 'Revenue_Growth', 'EPS_Consistency', 'Forward_PE', 'CCC']]
            })

            st.table(df)

if __name__ == "__main__":
    main()

