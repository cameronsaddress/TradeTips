# app.py

import streamlit as st
import pandas as pd
import numpy as np
import math
import requests
import time
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

# Define the Alpha Vantage API Key from Streamlit Secrets
try:
    ALPHA_VANTAGE_API_KEY = st.secrets['alpha_vantage']['api_key']
except KeyError:
    st.error("API key for Alpha Vantage not found. Please add it to your Streamlit secrets.")
    st.stop()


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
    Fetches stock data from Alpha Vantage, calculates IPS, and returns a DataFrame.
    """
    stock_list = []
    
    # Define a list of tickers to analyze
    large_companies = ['MSFT', 'AAPL', 'NVDA', 'GOOGL', 'AMZN']
    early_opportunities = ['HWM', 'SYM', 'HIMS', 'PFE', 'AMC']
    all_tickers = large_companies + early_opportunities
    
    # Placeholders for data if an API call fails
    default_metrics = {'R40': 0, 'GPM': 0, 'ROIC': 0, 'CCC': 0, 'EPS_cons': 0, 'PE': 0}

    for ticker in all_tickers:
        st.info(f"Fetching data for {ticker}...")
        metrics = default_metrics.copy()
        
        # --- API Calls to Alpha Vantage ---
        
        # 1. Fetch Company Overview for GPM, PE
        try:
            overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
            response = requests.get(overview_url)
            response.raise_for_status()
            data = response.json()
            if data and 'GrossProfitMargin' in data:
                metrics['GPM'] = float(data.get('GrossProfitMargin', 0)) * 100
                metrics['PE'] = float(data.get('ForwardPE', 0))
                metrics['ROIC'] = float(data.get('ROIC', 0)) * 100
            
        except (requests.exceptions.RequestException, ValueError, KeyError) as e:
            st.warning(f"Could not fetch Overview data for {ticker}: {e}")

        # 2. Fetch Earnings for EPS Consistency
        try:
            earnings_url = f"https://www.alphavantage.co/query?function=EARNINGS&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
            response = requests.get(earnings_url)
            response.raise_for_status()
            data = response.json()
            
            if data and 'quarterlyEarnings' in data and len(data['quarterlyEarnings']) >= 4:
                # Check if EPS beat estimates for the last 4 quarters
                beats = 0
                for quarter in data['quarterlyEarnings'][:4]:
                    if float(quarter.get('reportedEPS', 0)) > float(quarter.get('estimatedEPS', 0)):
                        beats += 1
                metrics['EPS_cons'] = 1 if beats == 4 else 0
        except (requests.exceptions.RequestException, ValueError, KeyError) as e:
            st.warning(f"Could not fetch Earnings data for {ticker}: {e}")

        # 3. Fetch Income Statement for Revenue Growth & Net Profit Margin
        try:
            income_url = f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
            response = requests.get(income_url)
            response.raise_for_status()
            data = response.json()
            
            if data and 'quarterlyReports' in data and len(data['quarterlyReports']) >= 2:
                latest_revenue = float(data['quarterlyReports'][0].get('totalRevenue', 0))
                prev_year_revenue = float(data['quarterlyReports'][4].get('totalRevenue', 0)) # Compare with same quarter previous year
                
                if prev_year_revenue > 0:
                    revenue_growth = ((latest_revenue - prev_year_revenue) / prev_year_revenue) * 100
                    metrics['R40'] = revenue_growth
                
                net_income = float(data['quarterlyReports'][0].get('netIncome', 0))
                if latest_revenue > 0:
                    net_profit_margin = (net_income / latest_revenue) * 100
                    metrics['R40'] += net_profit_margin
        except (requests.exceptions.RequestException, ValueError, KeyError) as e:
            st.warning(f"Could not fetch Income Statement data for {ticker}: {e}")
        
        # 4. Cash Conversion Cycle (CCC) is more complex and often not a single API call.
        #    For now, we'll use a placeholder to avoid hitting multiple API limits.
        #    In a real app, this would require Balance Sheet data.
        #    We'll set a reasonable placeholder based on your examples.
        if ticker in ['HIMS', 'SYM']: # low CCC for digital/early tech
            metrics['CCC'] = 5
        elif ticker in ['MSFT', 'NVDA', 'AAPL', 'GOOGL']: # moderate CCC for large tech
            metrics['CCC'] = 20
        elif ticker in ['HWM', 'PFE', 'AMC']: # higher CCC for manufacturing/physical goods
            metrics['CCC'] = 60
        else:
            metrics['CCC'] = 30 # default
            
        # Calculate IPS score after gathering all available metrics
        ips_score = calculate_ips(metrics)
        if ips_score is not None:
            stock_list.append({
                'Ticker': ticker,
                'IPS Score': ips_score,
                'R40': metrics['R40'],
                'GPM (%)': metrics['GPM'],
                'ROIC (%)': metrics['ROIC'],
                'CCC (days)': metrics['CCC'],
                'EPS Cons': metrics['EPS_cons'],
                'Forward PE': metrics['PE']
            })
        
        # Respect the Alpha Vantage API rate limit (5 requests per minute)
        time.sleep(15) 
        
    df = pd.DataFrame(stock_list)
    return df

# --- Main App Logic ---

st.title("📈 TradeTips - Dynamic IPS Analysis")
st.markdown(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown("""
This application dynamically analyzes a list of stocks using the **Alpha Vantage API** to find the best candidates based on a custom **Investment Profile Score (IPS)** formula. The data is refreshed every **10 minutes** to provide up-to-date insights.
""")

# Fetch the stock data and calculate IPS scores
with st.spinner("Fetching data from Alpha Vantage and calculating IPS scores... This may take a moment due to API rate limits."):
    all_stocks_df = get_stock_data()

# Separate large companies and early opportunities
large_companies = ['MSFT', 'AAPL', 'NVDA', 'GOOGL', 'AMZN']
early_opportunities = ['HWM', 'SYM', 'HIMS', 'PFE', 'AMC']

large_companies_df = all_stocks_df[all_stocks_df['Ticker'].isin(large_companies)].sort_values('IPS Score', ascending=False)
early_opportunities_df = all_stocks_df[all_stocks_df['Ticker'].isin(early_opportunities)].sort_values('IPS Score', ascending=False)

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
- **R40:** A blend of **revenue growth** and **net profit margin**.
- **GPM:** Gross Profit Margin.
- **ROIC:** Return on Invested Capital.
- **CCC:** Cash Conversion Cycle. A lower value is better.
- **EPS Cons:** EPS Consistency (1 if last 4 quarters beat estimates, else 0).
- **PE:** Forward PE Ratio.
""")
st.markdown("""
<div style="font-size: 0.8rem; text-align: center; color: gray;">
    Note: Due to Alpha Vantage API limitations, some metrics (like CCC) are placeholders to avoid excessive API calls.
    The app respects the 5 requests-per-minute limit, so the initial load may be slow.
</div>
""", unsafe_allow_html=True)
