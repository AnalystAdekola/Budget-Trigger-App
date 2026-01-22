import streamlit as st
import pandas as pd
import requests
import json
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. THEME & UI ---
st.set_page_config(page_title="Budget AI Monitor", page_icon="🚶‍♂️")

# Man walking into door top corner theme
st.markdown("""
    <style>
    .corner-theme {
        position: absolute;
        top: -60px;
        right: 10px;
        font-size: 45px;
        z-index: 100;
    }
    .stApp {
        border-top: 8px solid #4CAF50;
    }
    </style>
    <div class="corner-theme">🚶‍♂️🚪</div>
    """, unsafe_allow_html=True)

# --- 2. KEYS & INITIALIZATION ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    SLACK_WEBHOOK = st.secrets["SLACK_WEBHOOK"]
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash", 
        google_api_key=GOOGLE_API_KEY,
        temperature=0
    )
except KeyError:
    st.error("Missing Secrets! Add GOOGLE_API_KEY and SLACK_WEBHOOK to Streamlit Cloud Secrets.")
    st.stop()

# --- 3. DATA ENGINE ---
def load_data():
    try:
        df = pd.read_csv("Budget Trigger App.csv")
        # Normalize columns to lowercase immediately
        df.columns = df.columns.str.strip().str.lower()
        
        # Ensure numeric types
        df['budgeted'] = pd.to_numeric(df['budgeted'])
        df['actual'] = pd.to_numeric(df['actual'])
        
        df['variance'] = df['actual'] - df['budgeted']
        df['variance_%'] = (df['variance'] / df['budgeted']) * 100
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        st.stop()

def get_ai_insight(dept, budgeted, actual, variance_pct):
    # Standardizing inputs as strings to prevent API crashes
    prompt = f"Dept: {dept}, Budget: {budgeted}, Actual: {actual}, Variance: {variance_pct:.2f}%. Is this critical?"
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"AI Analysis Unavailable: {str(e)}"

# --- 4. MAIN APP ---
st.title("💰 Budget Compliance Monitor")
data = load_data()

st.subheader("Current Spend Data")
st.dataframe(data.style.highlight_max(axis=0, subset=['variance_%'], color='#ff4b4b'))

if st.button("🚀 Run AI Audit"):
    # We use a 5% threshold
    overspenders = data[data['variance_%'] > 5.0]
    
    if not overspenders.empty:
        for _, row in overspenders.iterrows():
            with st.spinner(f"Reviewing {row['department']}..."):
                # Using the exact lowercase names that load_data() created
                insight = get_ai_insight(
                    row['department'], 
                    row['budgeted'], 
                    row['actual'], 
                    row['variance_%']
                )
                
                st.warning(f"**{row['department'].title()} Alert:** {insight}")
                
                # Send to Slack
                msg = f"Budget Alert: {row['department'].upper()}\nInsight: {insight}"
                requests.post(SLACK_WEBHOOK, json={"text": msg})
        st.success("Manager notified via Slack.")
    else:
        st.success("All budgets are compliant.")
