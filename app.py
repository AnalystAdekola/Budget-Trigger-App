import streamlit as st
import pandas as pd
import requests
import json
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="Budget AI Monitor", page_icon="💰")

# Securely load keys from Streamlit Secrets
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
SLACK_WEBHOOK = st.secrets["SLACK_WEBHOOK"]

# Initialize AI (Gemini 1.5 Flash is best for speed/cost)
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GOOGLE_API_KEY)

# --- 2. DATA ENGINE ---
def load_data():
    df = pd.read_csv("Budget Trigger App.csv")
    # Calculate Variance
    df['Variance'] = df['actual'] - df['budgeted']
    df['Variance_%'] = (df['Variance'] / df['budgeted']) * 100
    return df

def get_ai_insight(dept, budgeted, actual, variance_pct):
    prompt = f"""
    You are a Senior Financial Controller. 
    The {dept} department spent ${actual:,} against a budget of ${budgeted:,} ({variance_pct:.1f}% variance).
    Context: It is currently January (a high-growth launch month). 
    Is this variance critical or expected? Give a 1-sentence recommendation.
    """
    return llm.invoke(prompt).content

def send_slack(message):
    requests.post(SLACK_WEBHOOK, data=json.dumps({"text": message}))

# --- 3. USER INTERFACE ---
st.title("💰 Budget Compliance Monitor")
data = load_data()
st.table(data)

if st.button("Run AI Audit"):
    # Filter for anything over 5% variance
    triggers = data[data['Variance_%'] > 5.0]
    
    if not triggers.empty:
        for _, row in triggers.iterrows():
            with st.spinner(f"AI Analyzing {row['department']}..."):
                insight = get_ai_insight(row['department'], row['budgeted'], row['actual'], row['Variance_%'])
                
                # Display in App
                st.warning(f"**{row['department']} Alert:** {insight}")
                
                # Send to Slack
                send_slack(f"🚨 *Budget Alert: {row['department']}*\nInsight: {insight}")
        st.success("Audit complete. Manager notified via Slack.")
    else:
        st.success("All departments are within the safe threshold.")