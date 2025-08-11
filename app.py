# app.py

import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import datetime

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


# --- Caching Data Fetching ---
# Caching the data retrieval function to prevent repeated API calls
# This makes the app faster and avoids rate-limiting issues from Yahoo Finance
@st.cache_data
def get_stock_data(ticker, period="1mo"):
    """
    Downloads stock data and handles potential errors gracefully.
    Returns a pandas DataFrame or None on failure.
    """
    try:
        data = yf.download(ticker, period=period)
        if data.empty:
            st.warning(f"No data returned for ticker: {ticker}. Check the ticker symbol.")
            return None
        return data
    except Exception as e:
        st.error(f"An error occurred while fetching data for {ticker}: {e}")
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
            data = get_stock_data(ticker, period="1y")

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
                    prev_close = data['Close'].iloc[-2]
                    change = last_price - prev_close
                    percent_change = (change / prev_close) * 100
                    
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
    large_results = [get_stock_data(t, period="1d") for t in large_companies]
    
    st.markdown("Based on recent market trends, these large-cap stocks may be worth watching.")
    
    # Displaying metrics and charts for large companies
    if large_results and large_results[0] is not None:
        first_ticker = large_companies[0]
        st.write(f"**{first_ticker} Price Trend (1 month)**")
        data = get_stock_data(first_ticker, period="1mo")
        if data is not None:
            st.line_chart(data['Close'])
        else:
            st.warning(f"Could not retrieve chart data for {first_ticker}.")
    
    cols = st.columns(len(large_companies))
    for i, ticker in enumerate(large_companies):
        data = large_results[i]
        if data is not None:
            with cols[i]:
                last_price = data['Close'].iloc[-1]
                st.metric(label=f"Last Price for {ticker}", value=f"${last_price:,.2f}")

with tabs_market[1]:
    st.subheader("Potential Early Opportunities")
    early_opportunities = early_opportunities_placeholder
    early_results = [get_stock_data(t, period="1d") for t in early_opportunities]
    
    st.markdown("Here are some smaller companies showing recent activity that could present early opportunities.")
    
    # Displaying metrics and charts for early opportunities
    if early_results and early_results[0] is not None:
        first_ticker = early_opportunities[0]
        st.write(f"**{first_ticker} Price Trend (1 month)**")
        data = get_stock_data(first_ticker, period="1mo")
        if data is not None:
            st.line_chart(data['Close'])
        else:
            st.warning(f"Could not retrieve chart data for {first_ticker}.")
            
    cols = st.columns(len(early_opportunities))
    for i, ticker in enumerate(early_opportunities):
        data = early_results[i]
        if data is not None:
            with cols[i]:
                last_price = data['Close'].iloc[-1]
                st.metric(label=f"Last Price for {ticker}", value=f"${last_price:,.2f}")

# End of script
