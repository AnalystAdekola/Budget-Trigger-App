import streamlit as st
import pandas as pd
import requests
import json
import time
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. SETUP ---
st.set_page_config(page_title="Budget AI Monitor", page_icon="💰")

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    SLACK_WEBHOOK = st.secrets["SLACK_WEBHOOK"]
    
    # We keep 2.0 Flash but add retry logic
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        google_api_key=GOOGLE_API_KEY,
        max_retries=2, 
        timeout=30
    )
except KeyError:
    st.error("Add GOOGLE_API_KEY and SLACK_WEBHOOK to Streamlit Secrets.")
    st.stop()

# --- 2. THE BATCH FIX ---
def get_batch_ai_insights(overspenders_df):
    """Analyzes all overspending departments in ONE single API call to save quota."""
    # Convert the dataframe to a simple text summary
    summary = overspenders_df[['department', 'variance_%']].to_string(index=False)
    
    prompt = f"""
    Review these overspending departments:
    {summary}
    
    For each department, provide a 1-sentence risk assessment. 
    Format your response exactly like this:
    DEPT_NAME: Insight text
    """
    
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. DATA ENGINE ---
def load_data():
    df = pd.read_csv("Budget Trigger App.csv")
    df.columns = df.columns.str.strip().str.lower()
    df['budgeted'] = pd.to_numeric(df['budgeted'], errors='coerce').fillna(0)
    df['actual'] = pd.to_numeric(df['actual'], errors='coerce').fillna(0)
    df['variance_%'] = df.apply(lambda x: (x['actual'] - x['budgeted']) / x['budgeted'] * 100 if x['budgeted'] != 0 else 0, axis=1)
    return df

# --- 4. UI ---
st.title("💰 Budget Compliance Monitor")
data = load_data()
st.dataframe(data)

if st.button("🚀 Run AI Audit"):
    overspenders = data[data['variance_%'] > 5.0]
    
    if not overspenders.empty:
        with st.spinner("Analyzing all departments in one go..."):
            # SINGLE CALL: This prevents the 429 error
            full_insight = get_batch_ai_insights(overspenders)
            
            st.info("### AI Audit Results")
            st.markdown(full_insight)
            
            # Send one consolidated summary to Slack
            requests.post(SLACK_WEBHOOK, json={"text": f"📊 *Consolidated Budget Audit:*\n{full_insight}"})
            st.success("Manager notified.")
    else:
        st.success("All budgets compliant.")
