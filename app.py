import streamlit as st
import pandas as pd
import requests

# API key for Financial Modeling Prep (FMP)
try:
    # Attempt to get the key from the default location
    FMP_API_KEY = st.secrets.get("fmp_api_key")
    if not FMP_API_KEY:
        # If not found, try the nested location from the previous attempt
        FMP_API_KEY = st.secrets.get("FMP", {}).get("fmp_api_key")
except Exception as e:
    st.error(f"Error loading API key: {e}. Please ensure 'fmp_api_key' is set in your Streamlit secrets.")
    FMP_API_KEY = None

# FMP API base URL
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

@st.cache_data(ttl=3600)  # Cache data for 1 hour to avoid excessive API calls
def get_stock_data(symbol, api_key):
    """
    Fetches required financial data for a given stock from the FMP API.
    Returns a dictionary of metrics and the raw API responses.
    """
    if not api_key:
        return {}, {}
    
    metrics = {
        'GPM': None, 'ROIC': None, 'Revenue_Growth': None,
        'EPS_Consistency': None, 'Forward_PE': None, 'CCC': None,
        'error': None
    }
    raw_data = {}

    try:
        # A list of endpoints to fetch
        endpoints = {
            'Ratios': f"/ratios/{symbol}?period=quarter&limit=1&apikey={api_key}",
            'Income_Statement': f"/income-statement/{symbol}?period=quarter&limit=5&apikey={api_key}",
            'Earnings_Surprises': f"/earnings-surprises/{symbol}?limit=4&apikey={api_key}",
            'Quote': f"/quote/{symbol}?apikey={api_key}",
            'Balance_Sheet': f"/balance-sheet-statement/{symbol}?period=quarter&limit=2&apikey={api_key}"
        }

        for name, path in endpoints.items():
            url = FMP_BASE_URL + path
            response = requests.get(url)
            if response.status_code == 200 and response.json():
                raw_data[name] = response.json()
            else:
                raw_data[name] = "Data not available or API error"

        # Parsing the fetched data
        # GPM and ROIC
        if raw_data.get('Ratios') and isinstance(raw_data['Ratios'], list) and raw_data['Ratios'][0]:
            metrics['GPM'] = raw_data['Ratios'][0].get('grossProfitMargin')
            metrics['ROIC'] = raw_data['Ratios'][0].get('roic')

        # Revenue Growth
        if raw_data.get('Income_Statement') and len(raw_data['Income_Statement']) >= 4:
            current_revenue = raw_data['Income_Statement'][0].get('revenue')
            year_ago_revenue = raw_data['Income_Statement'][3].get('revenue')
            if current_revenue and year_ago_revenue and year_ago_revenue > 0:
                metrics['Revenue_Growth'] = (current_revenue - year_ago_revenue) / year_ago_revenue

        # EPS Consistency
        if raw_data.get('Earnings_Surprises') and len(raw_data['Earnings_Surprises']) >= 4:
            metrics['EPS_Consistency'] = all(
                surprise.get('actualEarningResult') >= surprise.get('estimatedEarning')
                for surprise in raw_data['Earnings_Surprises']
            )

        # Forward PE
        if raw_data.get('Quote') and raw_data['Quote'][0]:
            metrics['Forward_PE'] = raw_data['Quote'][0].get('pe')
        
        # CCC
        if (raw_data.get('Balance_Sheet') and raw_data['Balance_Sheet'][0] and
                raw_data.get('Income_Statement') and raw_data['Income_Statement'][0]):
            bs_latest = raw_data['Balance_Sheet'][0]
            inc_latest = raw_data['Income_Statement'][0]

            cogs_ttm = inc_latest.get('costOfRevenue', 0) * 4
            revenue_ttm = inc_latest.get('revenue', 0) * 4
            inventory = bs_latest.get('inventory', 0)
            receivables = bs_latest.get('receivables', 0)
            payables = bs_latest.get('accountPayables', 0)

            if cogs_ttm > 0 and revenue_ttm > 0:
                dio = (inventory / cogs_ttm) * 365
                dso = (receivables / revenue_ttm) * 365
                dpo = (payables / cogs_ttm) * 365
                metrics['CCC'] = dio + dso - dpo

    except Exception as e:
        metrics['error'] = f"An error occurred while fetching or parsing data: {e}"

    return metrics, raw_data

def get_ips_grade(metrics):
    """
    Grades a stock based on the IPS criteria using a simple scoring system.
    Returns the grade and a dictionary of reasons.
    """
    score = 0
    reasons = {}

    criteria = {
        'GPM': (lambda x: x > 0.40, "Gross Profit Margin (GPM) > 40%"),
        'ROIC': (lambda x: x > 0.10, "Return on Invested Capital (ROIC) > 10%"),
        'Revenue_Growth': (lambda x: x > 0.10, "Revenue Growth > 10%"),
        'EPS_Consistency': (lambda x: x is True, "Consistent EPS beats (last 4 qtrs)"),
        'Forward_PE': (lambda x: x < 20, "Forward P/E < 20"),
        'CCC': (lambda x: x < 30, "Cash Conversion Cycle (CCC) < 30 days")
    }

    for metric, (check, description) in criteria.items():
        value = metrics.get(metric)
        if value is not None:
            if check(value):
                score += 1
                reasons[metric] = f"✅ {description}"
            else:
                reasons[metric] = f"❌ {description}"
        else:
            reasons[metric] = f"⚠️ {description} (Data not available)"

    if score >= 5: grade = "A (Strong Buy)"
    elif score >= 3: grade = "B (Consider Buy)"
    elif score >= 1: grade = "C (Hold)"
    else: grade = "D (Sell)"
    
    return grade, reasons, score

def main():
    try:
        st.set_page_config(page_title="IPS Stock Screener", layout="wide")

        # Custom CSS for a better look and feel
        st.markdown("""
            <style>
            .main-header { font-size: 3rem; font-weight: bold; color: #4CAF50; text-align: center; margin-bottom: 0.5em; }
            .subheader { font-size: 1.5rem; color: #555; text-align: center; margin-bottom: 2em; }
            .grade-card { text-align: center; font-size: 2em; font-weight: bold; padding: 1em; border-radius: 15px; color: white; margin-top: 1em; }
            .grade-A { background-color: #4CAF50; }
            .grade-B { background-color: #FFC107; }
            .grade-C { background-color: #2196F3; }
            .grade-D { background-color: #F44336; }
            </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="main-header">IPS Stock Screener</div>', unsafe_allow_html=True)
        st.markdown('<div class="subheader">Grade stocks based on the IPS financial framework</div>', unsafe_allow_html=True)

        if not FMP_API_KEY:
            st.warning("Please add your Financial Modeling Prep API key to the Streamlit secrets to continue.")
            return

        st.sidebar.header("What is IPS?")
        st.sidebar.markdown("""
        The **Investment Philosophy Score (IPS)** is a framework to evaluate stocks based on a set of fundamental metrics.
        A stock receives a point for each of the following criteria it meets:
        1.  **GPM > 40%**
        2.  **ROIC > 10%**
        3.  **Revenue Growth > 10%**
        4.  **EPS Consistency**
        5.  **Forward PE < 20**
        6.  **CCC < 30 days**
        Based on the total score, a grade is assigned:
        * **A**: 5-6 points (Strong Buy)
        * **B**: 3-4 points (Consider Buy)
        * **C**: 1-2 points (Hold)
        * **D**: 0 points (Sell)
        """)

        with st.form("stock_form"):
            ticker = st.text_input("Enter a stock ticker (e.g., AAPL)", value="AAPL").upper()
            submit_button = st.form_submit_button("Analyze Stock")

        if submit_button:
            with st.spinner("Fetching and analyzing data..."):
                stock_metrics, raw_data = get_stock_data(ticker, FMP_API_KEY)
            
            if stock_metrics.get('error'):
                st.error(stock_metrics['error'])
            else:
                grade, reasons, score = get_ips_grade(stock_metrics)
                st.markdown(f"### Results for {ticker}")
                
                analysis_tab, raw_data_tab = st.tabs(["Analysis", "Raw Data"])
                
                with analysis_tab:
                    grade_color_class = f"grade-{grade.split()[0]}"
                    st.markdown(f'<div class="grade-card {grade_color_class}">{grade}</div>', unsafe_allow_html=True)
                    st.markdown("### IPS Criteria Breakdown")
                    
                    df = pd.DataFrame({
                        'Metric': ['GPM', 'ROIC', 'Revenue Growth', 'EPS Consistency', 'Forward PE', 'CCC'],
                        'Criteria': ['> 40%', '> 10%', '> 10%', 'Beat estimates', '< 20', '< 30 days'],
                        'Meets Criteria': [reasons[k] for k in ['GPM', 'ROIC', 'Revenue_Growth', 'EPS_Consistency', 'Forward_PE', 'CCC']]
                    })
                    st.table(df)
                
                with raw_data_tab:
                    st.markdown("### Raw JSON Data from FMP API")
                    for title, data in raw_data.items():
                        with st.expander(f"Show {title} Data"):
                            st.json(data)
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()

