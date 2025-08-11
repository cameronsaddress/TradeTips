# app.py

import streamlit as st
import pandas as pd
import numpy as np
import math

# --- Configuration and Styling ---
st.set_page_config(
    page_title="TradeTips - IPS Analysis",
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
        r40 = metrics['R40']
        gpm = metrics['GPM']
        roic = metrics['ROIC']
        ccc = metrics['CCC']
        eps_cons = metrics['EPS_cons']
        pe = metrics['PE']
        
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
    except KeyError as e:
        st.error(f"Missing metric for IPS calculation: {e}")
        return None
    except Exception as e:
        st.error(f"Error calculating IPS score: {e}")
        return None


# --- Simulated Data Fetch (based on user's prompt) ---
# This dictionary holds all the hardcoded data provided by the user.
simulated_data = {
    'MSFT': {
        'R40': 53.63, 'GPM': 68.82, 'ROIC': 20.51, 'CCC': 10, 'EPS_cons': 1, 'PE': 30
    },
    'AAPL': {
        'R40': 31.00, 'GPM': 46.00, 'ROIC': 30.00, 'CCC': 20, 'EPS_cons': 1, 'PE': 28
    },
    'NVDA': {
        'R40': 130.00, 'GPM': 75.00, 'ROIC': 40.00, 'CCC': 15, 'EPS_cons': 1, 'PE': 40
    },
    'HWM': {
        'R40': 35.00, 'GPM': 30.00, 'ROIC': 12.00, 'CCC': 60, 'EPS_cons': 1, 'PE': 25
    },
    'SYM': {
        'R40': 45.00, 'GPM': 20.00, 'ROIC': -10.00, 'CCC': 30, 'EPS_cons': 0, 'PE': 50
    },
    'HIMS': {
        'R40': 50.00, 'GPM': 80.00, 'ROIC': 15.00, 'CCC': 5, 'EPS_cons': 1, 'PE': 20
    }
}

# --- Main App Logic ---
st.title("📈 TradeTips - IPS Analysis")
st.markdown("""
Welcome to TradeTips! This application calculates the **Investment Profile Score (IPS)** for a selection of stocks based on a custom formula.
The IPS is designed to highlight stocks with strong growth, efficiency, and favorable valuation metrics.
""")

# Define the stock categories
large_companies = ['MSFT', 'AAPL', 'NVDA']
early_opportunities = ['HWM', 'SYM', 'HIMS']

# Calculate IPS for all stocks and store in a DataFrame
all_stocks_data = []
for ticker, metrics in simulated_data.items():
    ips_score = calculate_ips(metrics)
    if ips_score is not None:
        all_stocks_data.append({
            'Ticker': ticker,
            'IPS Score': ips_score,
            'R40': metrics['R40'],
            'GPM (%)': metrics['GPM'],
            'ROIC (%)': metrics['ROIC'],
            'CCC (days)': metrics['CCC'],
            'EPS Cons': metrics['EPS_cons'],
            'Forward PE': metrics['PE']
        })

df_all = pd.DataFrame(all_stocks_data).round(2)
df_all = df_all.set_index('Ticker')

# --- Display Results ---

st.header("Large Companies (Top by Market Cap)")
st.markdown("Here are the top large-cap stocks, sorted by their IPS score.")
df_large = df_all.loc[large_companies].sort_values(by='IPS Score', ascending=False)
st.dataframe(df_large)

st.header("Potential Early Opportunities")
st.markdown("These emerging growth stocks are sorted by their IPS score, highlighting potential high-growth plays.")
df_early = df_all.loc[early_opportunities].sort_values(by='IPS Score', ascending=False)
st.dataframe(df_early)

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

# End of script
