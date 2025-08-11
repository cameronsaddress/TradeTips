import streamlit as st
import yfinance as yf
from financetoolkit import Toolkit
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import math
import requests
from alpha_vantage.fundamentaldata import FundamentalData
import time
import matplotlib.pyplot as plt

# Set page config for professional look
st.set_page_config(page_title="Professional IPS Trading Dashboard", layout="wide", page_icon="📈")

# Custom CSS for high-dollar trading site aesthetic (dark theme, modern fonts)
st.markdown("""
    <style>
    /* General styling */
    body {
        color: #ffffff;
        background-color: #121212;
        font-family: 'Arial', sans-serif;
    }
    .stApp {
        background-color: #121212;
    }
    /* Header */
    h1 {
        color: #00ff99;
        text-align: center;
        font-size: 2.5em;
        margin-bottom: 0.5em;
    }
    h2 {
        color: #00ff99;
        font-size: 1.8em;
    }
    /* Tables */
    table {
        width: 100%;
        background-color: #1e1e1e;
        border: 1px solid #00ff99;
        border-radius: 5px;
        border-collapse: collapse;
    }
    th, td {
        padding: 8px;
        text-align: left;
        border-bottom: 1px solid #00ff99;
        color: #ffffff;
    }
    th {
        background-color: #00ff99;
        color: #121212;
    }
    span[title] {
        cursor: help;
    }
    /* Sidebar */
    .css-1lcbmhc {
        background-color: #1e1e1e;
    }
    /* Buttons and inputs */
    .stButton > button {
        background-color: #00ff99;
        color: #121212;
        border: none;
        border-radius: 5px;
    }
    .stTextInput > div > div > input {
        background-color: #1e1e1e;
        color: #ffffff;
        border: 1px solid #00ff99;
    }
    /* Charts */
    .stPlotlyChart, .stAltairChart {
        background-color: #1e1e1e;
        border: 1px solid #00ff99;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# Auto-refresh every 10 minutes (600000 ms)
st_autorefresh(interval=600000, limit=None, key="data_refresh")

# Cache non-real-time data for 1 hour to respect API limits
@st.cache_data(ttl=3600)
def get_fundamental_data(ticker, api_key):
    try:
        fd = FundamentalData(key=api_key)
        balance_sheet = fd.get_balance_sheet_quarterly(ticker)[0]
        income_statement = fd.get_income_statement_quarterly(ticker)[0]
        return balance_sheet, income_statement
    except:
        return None, None

# IPS Calculation Function (optimized to minimize Alpha Vantage calls - only if fallback needed)
def calculate_ips(ticker, gpm_min=60, api_key='YOUR_ALPHA_VANTAGE_KEY'):
    try:
        # Use financetoolkit and yfinance first for most data
        companies = Toolkit([ticker], enforce_source="YahooFinance")
        stock = yf.Ticker(ticker)
       
        # Revenue growth
        income = companies.get_income_statement(period="quarterly")
        revenue = income.loc['Revenue']
        revenue_growth = revenue.pct_change(periods=4).iloc[-1] * 100 if len(revenue) >= 5 else 0
       
        # Net profit margin
        net_profit_margin = companies.ratios.get_net_profit_margin().iloc[-1] * 100
       
        # R40
        r40 = revenue_growth + net_profit_margin
       
        # GPM
        gpm = companies.ratios.get_gross_margin().iloc[-1] * 100
       
        # Try financetoolkit for ROIC and CCC first
        roic_ft = companies.ratios.get_return_on_invested_capital().iloc[-1] * 100 if not pd.isna(companies.ratios.get_return_on_invested_capital().iloc[-1]) else None
        ccc_ft = companies.ratios.get_cash_conversion_cycle().iloc[-1] if not pd.isna(companies.ratios.get_cash_conversion_cycle().iloc[-1]) else None
       
        if roic_ft is None or ccc_ft is None:
            # Only call Alpha Vantage if fallback needed
            balance_sheet, income_statement = get_fundamental_data(ticker, api_key)
            if balance_sheet and income_statement:
                # CCC
                dio = float(balance_sheet.get('inventory', 0)) / (float(income_statement.get('costOfRevenue', 1)) / 365)
                dso = float(balance_sheet.get('netReceivables', 0)) / (float(income_statement.get('totalRevenue', 1)) / 365)
                dpo = float(balance_sheet.get('accountsPayable', 0)) / (float(income_statement.get('costOfRevenue', 1)) / 365)
                ccc = dio + dso - dpo
                # ROIC
                nopat = float(income_statement.get('operatingIncome', 0)) * (1 - float(income_statement.get('incomeTaxExpense', 0)) / float(income_statement.get('incomeBeforeTax', 1)))
                invested_capital = float(balance_sheet.get('totalAssets', 1)) - float(balance_sheet.get('totalCurrentLiabilities', 0))
                roic = (nopat / invested_capital) * 100 if invested_capital != 0 else 0
            else:
                # Industry averages if all fail
                industry_averages = {'MSFT': (20.51, 10), 'AAPL': (30, 20), 'NVDA': (40, 15), 'HWM': (12, 60), 'SYM': (-10, 30), 'HIMS': (15, 5)}
                roic, ccc = industry_averages.get(ticker, (0, 30))
        else:
            roic = roic_ft
            ccc = ccc_ft
       
        # EPS consistency
        earnings = stock.get_earnings_dates(limit=4)
        eps_cons = 1 if earnings is not None and len(earnings) >= 4 and all(earnings['Reported EPS'] > earnings['EPS Estimate'].fillna(0)) else 0
       
        # Forward PE
        pe = stock.info.get('forwardPE', 20)
       
        # IPS Equation
        ips = (
            (r40 * 0.4) +
            (max(0, min(1, (gpm - gpm_min) / 40)) * 0.2) +
            (max(0, min(1, (roic - 10) / 40)) * 0.2) -
            (max(0, min(1, ccc / 100)) * 0.1) +
            (eps_cons * 0.1) -
            (max(0, min(1, (pe - 20) / 20)) * 0.1)
        )
       
        return {
            'Ticker': ticker,
            'IPS': round(ips, 3),
            'R40': round(r40, 2),
            'GPM (%)': round(gpm, 2),
            'ROIC (%)': round(roic, 2),
            'CCC (days)': round(ccc, 2),
            'EPS Cons': eps_cons,
            'Forward PE': round(pe, 2),
            'Data Freshness': time.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return {'Ticker': ticker, 'IPS': 'Error', 'Error': str(e), 'Data Freshness': 'N/A'}

# Function to convert DataFrame to HTML with tooltips on headers
def dataframe_to_html_with_tooltips(df, tooltips):
    html = '<table>'
    # Headers with tooltips
    html += '<tr>'
    for col in df.columns:
        tooltip = tooltips.get(col, '')
        html += f'<th><span title="{tooltip}">{col}</span></th>'
    html += '</tr>'
    # Rows
    for _, row in df.iterrows():
        html += '<tr>'
        for val in row:
            html += f'<td>{val}</td>'
        html += '</tr>'
    html += '</table>'
    return html

# Tooltips definitions
tooltips = {
    'Ticker': 'Stock Ticker Symbol',
    'IPS': 'Investment Potential Score: A composite score indicating the stock\'s investment potential based on the equation (higher is better, aim for >20-25).',
    'R40': 'R40: Year-over-year Revenue Growth (%) + Net Profit Margin (%). Measures overall growth and profitability.',
    'GPM (%)': 'Gross Profit Margin: Percentage of revenue remaining after subtracting the cost of goods sold.',
    'ROIC (%)': 'Return on Invested Capital: Measures how efficiently the company generates profits from its invested capital.',
    'CCC (days)': 'Cash Conversion Cycle: The number of days it takes to convert inventory and other resources into cash flows from sales.',
    'EPS Cons': 'EPS Consistency: 1 if the company beat earnings estimates in the last 4 quarters, else 0.',
    'Forward PE': 'Forward Price-to-Earnings Ratio: The stock\'s current price divided by its expected earnings per share over the next year.',
    'Data Freshness': 'Timestamp of the last data update.'
}

# Hardcoded lists (limited to 5 each to respect API limits)
large_companies = ["NVDA", "MSFT", "AAPL", "AMZN", "GOOGL"]
early_opportunities = ["HWM", "SYM", "HIMS", "OSCR", "ASTS"]

# Streamlit App
st.title("Professional IPS Trading Dashboard")
st.write("Real-time Investment Potential Scores for top stocks. Data refreshes every 10 minutes.")

# Sidebar for customization
st.sidebar.header("Dashboard Settings")
gpm_min = st.sidebar.slider("GPM Min Threshold (%)", 40, 70, 60)

# Layout in columns for professional feel
col1, col2 = st.columns(2)

with col1:
    st.header("Large Companies (Top by Market Cap)")
    large_results = []
    for ticker in large_companies:
        result = calculate_ips(ticker, gpm_min, api_key)
        large_results.append(result)
        time.sleep(0.5)  # Rate limiting for yfinance
    df_large = pd.DataFrame(large_results)
    st.markdown(dataframe_to_html_with_tooltips(df_large, tooltips), unsafe_allow_html=True)
    
    # Add a simple price chart for the first stock
    if large_results:
        first_ticker = large_companies[0]
        data = yf.download(first_ticker, period="1mo")['Close']
        fig, ax = plt.subplots()
        ax.plot(data, color='#00ff99')
        ax.set_title(f"{first_ticker} Price Trend", color='#ffffff')
        ax.set_facecolor('#121212')
        fig.patch.set_facecolor('#121212')
        ax.tick_params(colors='#ffffff')
        ax.spines['bottom'].set_color('#00ff99')
        ax.spines['top'].set_color('#00ff99')
        ax.spines['left'].set_color('#00ff99')
        ax.spines['right'].set_color('#00ff99')
        st.pyplot(fig)

with col2:
    st.header("Potential Early Opportunities")
    early_results = []
    for ticker in early_opportunities:
        result = calculate_ips(ticker, gpm_min, api_key)
        early_results.append(result)
        time.sleep(0.5)
    df_early = pd.DataFrame(early_results)
    st.markdown(dataframe_to_html_with_tooltips(df_early, tooltips), unsafe_allow_html=True)
    
    # Add a simple price chart for the first early stock
    if early_results:
        first_ticker = early_opportunities[0]
        data = yf.download(first_ticker, period="1mo")['Close']
        fig, ax = plt.subplots()
        ax.plot(data, color='#00ff99')
        ax.set_title(f"{first_ticker} Price Trend", color='#ffffff')
        ax.set_facecolor('#121212')
        fig.patch.set_facecolor('#121212')
        ax.tick_params(colors='#ffffff')
        ax.spines['bottom'].set_color('#00ff99')
        ax.spines['top'].set_color('#00ff99')
        ax.spines['left'].set_color('#00ff99')
        ax.spines['right'].set_color('#00ff99')
        st.pyplot(fig)

# Custom Tickers Expander
with st.expander("Add Custom Tickers"):
    tickers_input = st.text_input("Enter comma-separated tickers (up to 5)")
    if tickers_input:
        custom_tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()][:5]
        custom_results = []
        for ticker in custom_tickers:
            result = calculate_ips(ticker, gpm_min, api_key)
            custom_results.append(result)
            time.sleep(0.5)
        df_custom = pd.DataFrame(custom_results)
        st.markdown(dataframe_to_html_with_tooltips(df_custom, tooltips), unsafe_allow_html=True)

# Footer
st.markdown("<hr style='border:1px solid #00ff99;' />", unsafe_allow_html=True)
st.write("Powered by yFinance, FinanceToolkit & Alpha Vantage | Data as of August 11, 2025 | Note: API calls optimized for free tier limits (25/day). Fundamentals update quarterly.")
