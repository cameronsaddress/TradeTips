# app.py

import streamlit as st
import pandas as pd
import numpy as np
import math
import investpy
from datetime import datetime

# --- Configuration and Styling ---
st.set_page_config(
    page_title="TradeTips - Dynamic IPS Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for a clean, modern look
st.markdown("""
<style>
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .st-emotion-cache-1cypcdb {
        background-color: #0d1117;
    }
    .st-emotion-cache-e370x9 {
        background-color: #161b22;
        border-radius: 0.5rem;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #58a6ff;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.2rem;
    }
    .stMetric {
        background-color: #161b22;
        padding: 1.5rem;
        border-radius: 0.75rem;
        border: 1px solid #30363d;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    }
    .dataframe {
        color: #c9d1d9;
    }
</style>
""", unsafe_allow_html=True)


# --- IPS Equation Calculation Function ---
def calculate_ips(metrics):
    """
    Calculates the IPS score based on the provided formula.
    
    Args:
        metrics (dict): A dictionary containing R40, GPM, ROIC, CCC, EPS_cons, and PE.
    
    Returns:
        float: The calculated IPS score.
    """
    try:
        r40 = metrics.get('R40', 0)
        gpm = metrics.get('GPM', 0)
        roic = metrics.get('ROIC', 0)
        ccc = metrics.get('CCC', 0)
        eps_cons = metrics.get('EPS_cons', 0)
        pe = metrics.get('PE', 0)
        
        # IPS formula components
        comp_r40 = r40 * 0.4
        comp_gpm = max(0, min(1, (gpm - 60) / 40)) * 0.2
        comp_roic = max(0, min(1, (roic - 10) / 40)) * 0.2
        comp_ccc = max(0, min(1, ccc / 100)) * 0.1
        comp_eps_cons = eps_cons * 0.1
        comp_pe = max(0, min(1, (pe - 20) / 20)) * 0.1
        
        # Final calculation
        ips = comp_r40 + comp_gpm + comp_roic - comp_ccc + comp_eps_cons - comp_pe
        return ips
    except Exception as e:
        st.error(f"Error calculating IPS score: {e}")
        return None

@st.cache_data(ttl=600)  # Caches the data for 10 minutes (600 seconds)
def get_stock_data():
    """
    Fetches a list of all stocks from major indices, then simulates fetching their metrics.
    In a real-world app, this would use a financial API to get real-time metrics.
    
    Returns:
        pd.DataFrame: A DataFrame of all stocks with their IPS scores.
    """
    stock_list = []
    
    # Simulate a larger pool of stocks for analysis
    all_tickers = ['MSFT', 'AAPL', 'NVDA', 'AMZN', 'GOOGL', 'TSLA', 'HWM', 'SYM', 'HIMS', 'PFE', 'AMC', 'V', 'JPM', 'XOM', 'JNJ', 'WMT', 'PG', 'MA', 'UNH']
    
    # This is a placeholder for real API calls to get metrics.
    # We will use your provided data and some simulated data for the rest.
    simulated_metrics = {
        'MSFT': {'R40': 53.63, 'GPM': 68.82, 'ROIC': 20.51, 'CCC': 10, 'EPS_cons': 1, 'PE': 30},
        'AAPL': {'R40': 31.00, 'GPM': 46.00, 'ROIC': 30.00, 'CCC': 20, 'EPS_cons': 1, 'PE': 28},
        'NVDA': {'R40': 130.00, 'GPM': 75.00, 'ROIC': 40.00, 'CCC': 15, 'EPS_cons': 1, 'PE': 40},
        'HWM': {'R40': 35.00, 'GPM': 30.00, 'ROIC': 12.00, 'CCC': 60, 'EPS_cons': 1, 'PE': 25},
        'SYM': {'R40': 45.00, 'GPM': 20.00, 'ROIC': -10.00, 'CCC': 30, 'EPS_cons': 0, 'PE': 50},
        'HIMS': {'R40': 50.00, 'GPM': 80.00, 'ROIC': 15.00, 'CCC': 5, 'EPS_cons': 1, 'PE': 20},
    }

    # Simulate fetching data for all tickers and calculating their IPS scores
    for ticker in all_tickers:
        # Use provided data if available, otherwise generate some placeholder data
        if ticker in simulated_metrics:
            metrics = simulated_metrics[ticker]
        else:
            metrics = {
                'R40': np.random.uniform(10, 60),
                'GPM': np.random.uniform(20, 80),
                'ROIC': np.random.uniform(5, 30),
                'CCC': np.random.uniform(5, 70),
                'EPS_cons': np.random.choice([0, 1]),
                'PE': np.random.uniform(15, 60)
            }
        
        ips_score = calculate_ips(metrics)
        if ips_score is not None:
            stock_list.append({
                'Ticker': ticker,
                'IPS Score': ips_score,
                **metrics
            })
    
    df = pd.DataFrame(stock_list)
    return df

# --- Main App Logic ---

st.title("📈 TradeTips - Dynamic IPS Analysis")
st.markdown(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown("""
This application dynamically analyzes a list of stocks to find the best candidates based on a custom **Investment Profile Score (IPS)** formula.
The data is refreshed every **10 minutes** to provide up-to-date insights.
""")

# Fetch the stock data and calculate IPS scores
with st.spinner("Fetching and calculating IPS scores..."):
    all_stocks_df = get_stock_data()

# Separate large companies and early opportunities based on a simple heuristic (e.g., a specific list)
# In a real app, this would be based on market capitalization
large_cap_tickers = ['MSFT', 'AAPL', 'NVDA', 'AMZN', 'GOOGL', 'TSLA', 'V', 'JPM', 'XOM', 'JNJ', 'WMT', 'PG', 'MA', 'UNH']
large_companies_df = all_stocks_df[all_stocks_df['Ticker'].isin(large_cap_tickers)].sort_values('IPS Score', ascending=False)
early_opportunities_df = all_stocks_df[~all_stocks_df['Ticker'].isin(large_cap_tickers)].sort_values('IPS Score', ascending=False)


# --- Display Results ---

st.header("Best Large Company Opportunities")
st.markdown("These are the top 5 large-cap stocks with the highest IPS scores.")
st.dataframe(large_companies_df.head(5).set_index('Ticker').round(2))

st.header("Best Early Opportunities")
st.markdown("These are the top 5 emerging stocks with the highest IPS scores.")
st.dataframe(early_opportunities_df.head(5).set_index('Ticker').round(2))


# --- Explanation Section ---
st.header("Understanding the IPS Score")
st.markdown("""
The IPS Score is a proprietary metric calculated using a weighted formula that combines several fundamental indicators:
- **R40:** A blend of **revenue growth** and **net profit margin**, with a strong weight (0.4) to reward efficient growth.
- **GPM (Gross Profit Margin) & ROIC (Return on Invested Capital):** These metrics measure profitability and efficiency. The formula rewards values above certain thresholds (60% for GPM, 10% for ROIC) and caps the reward at a maximum value.
- **CCC (Cash Conversion Cycle):** This metric measures how long it takes to convert investments into cash. A lower CCC is better, so its impact is negative in the formula.
- **EPS Cons:** A simple binary score (1 or 0) for **EPS consistency**, rewarding companies that consistently beat earnings estimates.
- **PE (Forward PE Ratio):** A measure of valuation. The formula penalizes companies with high P/E ratios (above 20), as they are considered more expensive.

The resulting score provides a single, easy-to-understand value to compare different stocks' fundamental health and growth prospects.
""")

st.markdown("""
<div style="font-size: 0.8rem; text-align: center; color: gray;">
    Note: Data in this app is for demonstration purposes. In a production environment,
    you would connect to a real-time financial data API to get the IPS metrics.
</div>
""", unsafe_allow_html=True)
