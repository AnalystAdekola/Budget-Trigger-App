import streamlit as st
import pandas as pd
import requests
import json
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="Budget AI Monitor", page_icon="🚪")

# Custom CSS to put a "Man Walking into Door" theme at the top corner
st.markdown("""
    <style>
    /* Positions an icon in the top right corner */
    .top-corner-icon {
        position: absolute;
        top: -50px;
        right: 0px;
        font-size: 50px;
    }
    </style>
    <div class="top-corner-icon">🚶‍♂️🚪</div>
    """, unsafe_allow_html=True)

# Securely load keys from Streamlit Secrets
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
SLACK_WEBHOOK = st.secrets["SLACK_WEBHOOK"]

# Initialize AI
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GOOGLE_API_KEY)

# --- 2. DATA ENGINE ---
def load_data():
    try:
        # Load your specific file
        df = pd.read_csv("Budget Trigger App.csv")
        
        # Clean column names (handles 'Department', 'Budgeted', 'Actual' automatically)
        df.columns = df.columns.str.strip().str.lower()
        
        # Calculate Variance using the new lowercase keys
        df['variance'] = df['actual'] - df['budgeted']
        df['variance_%'] = (df['variance'] / df['budgeted']) * 100
        return df
    except FileNotFoundError:
        st.error("🚨 File 'Budget Trigger App.csv' not found in GitHub.")
        st.stop()

def get_ai_insight(dept, budgeted, actual, variance_pct):
    prompt = f"""
    You are a Financial Controller. 
    The {dept} department spent ${actual:,.2f} vs a budget of ${budgeted:,.2f} ({variance_pct:.1f}% variance).
    Is this variance critical? Give a 1-sentence expert recommendation.
    """
    return llm.invoke(prompt).content

def send_slack(message):
    try:
        requests.post(SLACK_WEBHOOK, data=json.dumps({"text": message}))
    except:
        pass

# --- 3. UI ---
st.title("💰 Budget Compliance Monitor")
data = load_data()

# Show the table with original-style headers for the user
st.subheader("Current Department Spending")
st.dataframe(data[['department', 'budgeted', 'actual', 'variance_%']].style.format({"variance_%": "{:.2f}%"}))

if st.button("🚀 Run AI Compliance Audit"):
    # Check for overspenders (e.g., more than 5% over)
    triggers = data[data['variance_%'] > 5.0]
    
    if not triggers.empty:
        for _, row in triggers.iterrows():
            with st.spinner(f"Analyzing {row['department']}..."):
                insight = get_ai_insight(
                    row['department'], 
                    row['budgeted'], 
                    row['actual'], 
                    row['variance_%']
                )
                
                # Display Results
                st.warning(f"**{row['department'].upper()} ALERT:** {insight}")
                
                # Send to Slack
                send_slack(f"📊 *AI Budget Audit*\n*Dept:* {row['department']}\n*Insight:* {insight}")
        st.success("Audit complete. Slack pings sent.")
    else:
        st.success("No critical variances detected today.")
