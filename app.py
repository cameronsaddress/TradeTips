# app.py

import streamlit as st
import pandas as pd
import datetime
import numpy as np

# --- Configuration and Styling ---
st.set_page_config(
    page_title="TradeTips",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
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
</style>
""", unsafe_allow_html=True)


# --- Static Data Function ---
# This function replaces the yfinance call with hardcoded data
# It generates a DataFrame that mimics the structure of a yfinance response
def get_static_stock_data(ticker, period="1y"):
    """
    Generates static stock data for demonstration purposes.
    Returns a pandas DataFrame.
    """
    try:
        end_date = datetime.date.today()
        if period == "1y":
            start_date = end_date - datetime.timedelta(days=365)
        elif period == "1mo":
            start_date = end_date - datetime.timedelta(days=30)
        else: # Default to 1 day
            start_date = end_date - datetime.timedelta(days=1)

        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Base price for the ticker, making it somewhat realistic
        if ticker == 'MSFT':
            base_price = 450
        elif ticker == 'AAPL':
            base_price = 220
        elif ticker == 'NVDA':
            base_price = 1200
        elif ticker == 'GOOGL':
            base_price = 180
        elif ticker == 'HWM':
            base_price = 70
        elif ticker == 'PFE':
            base_price = 30
        elif ticker == 'AMC':
            base_price = 5
        else:
            base_price = 100
        
        # Generate some synthetic price movements
        prices = base_price + np.random.randn(len(date_range)).cumsum() * 0.5
        
        # Create a DataFrame
        data = pd.DataFrame({
            'Close': prices,
            'High': prices + np.random.rand(len(date_range)) * 1,
            'Low': prices - np.random.rand(len(date_range)) * 1,
            'Volume': np.random.randint(1_000_000, 10_000_000, len(date_range))
        }, index=date_range)
        
        return data
    except Exception as e:
        st.error(f"An error occurred while generating static data for {ticker}: {e}")
        return None

# Placeholder data for demonstration
early_opportunities_placeholder = ['HWM', 'PFE', 'AMC']
large_companies_placeholder = ['NVDA', 'MSFT', 'GOOGL', 'AAPL']
nasdaq_100_placeholder = ['MSFT', 'AAPL', 'NVDA', 'AMZN', 'GOOGL', 'META']

# --- Main App Logic ---
st.title("📈 TradeTips - Your Financial Assistant")
st.markdown("""
Welcome to TradeTips! This application helps you analyze potential trading opportunities by
fetching real-time stock data and highlighting key trends.
""")

# Use Streamlit's session state to store a list of tickers to fetch
if 'tickers_to_fetch' not in st.session_state:
    st.session_state.tickers_to_fetch = []

# --- Sidebar for User Input ---
with st.sidebar:
    st.header("Settings")
    search_term = st.text_input("Enter a stock ticker to analyze", placeholder="e.g., TSLA")

    if st.button("Add Ticker"):
        if search_term and search_term.upper() not in st.session_state.tickers_to_fetch:
            st.session_state.tickers_to_fetch.append(search_term.upper())
            st.success(f"Added {search_term.upper()} to the list.")
        elif search_term.upper() in st.session_state.tickers_to_fetch:
            st.info(f"{search_term.upper()} is already in your list.")
        else:
            st.warning("Please enter a valid ticker symbol.")

    if st.button("Clear Tickers"):
        st.session_state.tickers_to_fetch = []
        st.experimental_rerun()

    # Automatically add some placeholders if the list is empty
    if not st.session_state.tickers_to_fetch:
        st.markdown("---")
        st.info("Your ticker list is empty. Adding some defaults for demonstration.")
        st.session_state.tickers_to_fetch.extend(nasdaq_100_placeholder[:3])


# --- Display Tickers ---
st.subheader("Your Watchlist")
if st.session_state.tickers_to_fetch:
    cols = st.columns(len(st.session_state.tickers_to_fetch))
    for i, ticker in enumerate(st.session_state.tickers_to_fetch):
        with cols[i]:
            st.metric(label=f"Ticker", value=ticker)
else:
    st.info("Add some tickers to your watchlist from the sidebar.")


# --- Ticker Analysis Section ---
st.header("Ticker Analysis")
if st.session_state.tickers_to_fetch:
    tabs = st.tabs([ticker for ticker in st.session_state.tickers_to_fetch])

    for i, ticker in enumerate(st.session_state.tickers_to_fetch):
        with tabs[i]:
            st.subheader(f"Analyzing {ticker}")

            # Fetch data for the current ticker
            data = get_static_stock_data(ticker, period="1y")

            if data is not None:
                # Use a container for a cleaner look
                with st.container():
                    st.write(f"**Historical Close Price for {ticker}**")
                    st.line_chart(data['Close'])

                # Display key metrics
                with st.container():
                    st.write("**Key Metrics**")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    last_price = data['Close'].iloc[-1]
                    # Make sure there is a previous day to calculate the change
                    if len(data['Close']) > 1:
                        prev_close = data['Close'].iloc[-2]
                        change = last_price - prev_close
                        percent_change = (change / prev_close) * 100
                    else:
                        change = 0
                        percent_change = 0
                    
                    with col1:
                        st.metric(label="Current Price", value=f"${last_price:,.2f}")
                    with col2:
                        st.metric(label="Daily Change", value=f"${change:,.2f}", delta=f"{percent_change:,.2f}%")
                    with col3:
                        st.metric(label="52-Week High", value=f"${data['High'].max():,.2f}")
                    with col4:
                        st.metric(label="52-Week Low", value=f"${data['Low'].min():,.2f}")

                # Display the raw data
                with st.expander("Show Raw Data"):
                    st.dataframe(data.tail(10))

else:
    st.info("No tickers selected for analysis.")


# --- Placeholder sections from the original code (modified for robustness) ---
st.header("Market Opportunities")

tabs_market = st.tabs(["Large Cap Companies", "Early Opportunities"])

with tabs_market[0]:
    st.subheader("Potential Large Cap Opportunities")
    large_companies = large_companies_placeholder
    
    st.markdown("Based on recent market trends, these large-cap stocks may be worth watching.")
    
    if large_companies:
        cols = st.columns(len(large_companies))
        for i, ticker in enumerate(large_companies):
            data = get_static_stock_data(ticker, period="1d")
            if data is not None and not data.empty:
                with cols[i]:
                    last_price = data['Close'].iloc[-1]
                    st.metric(label=f"Last Price for {ticker}", value=f"${last_price:,.2f}")
            else:
                 with cols[i]:
                    st.warning(f"No data for {ticker}")

with tabs_market[1]:
    st.subheader("Potential Early Opportunities")
    early_opportunities = early_opportunities_placeholder
    
    st.markdown("Here are some smaller companies showing recent activity that could present early opportunities.")
    
    if early_opportunities:
        cols = st.columns(len(early_opportunities))
        for i, ticker in enumerate(early_opportunities):
            data = get_static_stock_data(ticker, period="1d")
            if data is not None and not data.empty:
                with cols[i]:
                    last_price = data['Close'].iloc[-1]
                    st.metric(label=f"Last Price for {ticker}", value=f"${last_price:,.2f}")
            else:
                with cols[i]:
                    st.warning(f"No data for {ticker}")

# End of script

