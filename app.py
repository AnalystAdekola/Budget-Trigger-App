import streamlit as st
import pandas as pd
import requests
import json
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Budget AI Monitor", page_icon="💰")

# --- 2. KEYS & INITIALIZATION ---
try:
    # These must be set in your Streamlit Cloud Secrets (Settings > Secrets)
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    SLACK_WEBHOOK = st.secrets["SLACK_WEBHOOK"]
    
    # UPDATED: Using Gemini 2.0 Flash
    # This model is faster and handles financial reasoning with better precision
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        google_api_key=GOOGLE_API_KEY,
        temperature=0
    )
except KeyError:
    st.error("Missing Secrets! Add GOOGLE_API_KEY and SLACK_WEBHOOK to Streamlit Cloud Secrets.")
    st.stop()

# --- 3. DATA ENGINE ---
def load_data():
    try:
        # Loading your specific file
        df = pd.read_csv("Budget Trigger App.csv")
        
        # Normalize column names to lowercase to prevent KeyErrors
        df.columns = df.columns.str.strip().str.lower()
        
        # Convert columns to numeric, forcing errors to NaN then filling them
        df['budgeted'] = pd.to_numeric(df['budgeted'], errors='coerce').fillna(0)
        df['actual'] = pd.to_numeric(df['actual'], errors='coerce').fillna(0)
        
        # Calculate Variance math
        df['variance'] = df['actual'] - df['budgeted']
        # Avoid division by zero if budget is 0
        df['variance_%'] = df.apply(
            lambda x: (x['variance'] / x['budgeted'] * 100) if x['budgeted'] != 0 else 0, 
            axis=1
        )
        return df
    except FileNotFoundError:
        st.error("🚨 File 'Budget Trigger App.csv' not found. Ensure it is in your GitHub root folder.")
        st.stop()
    except Exception as e:
        st.error(f"Error processing CSV: {e}")
        st.stop()

def get_ai_insight(dept, budgeted, actual, variance_pct):
    """Feeds budget data to Gemini 2.0 for contextual analysis."""
    prompt = (
        f"Context: Internal Budget Audit. "
        f"Department: {dept}, Budget: ${budgeted:,.2f}, Actual: ${actual:,.2f}, Variance: {variance_pct:.2f}%. "
        "Analyze if this overspend is a critical risk or a common operational fluctuation. "
        "Provide a concise, 1-sentence executive recommendation."
    )
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"AI Analysis Error: {str(e)}"

def send_slack(message):
    """Sends the final alert to your Slack channel via Webhook."""
    try:
        requests.post(SLACK_WEBHOOK, json={"text": message}, timeout=5)
    except Exception as e:
        st.error(f"Failed to send Slack alert: {e}")

# --- 4. MAIN USER INTERFACE ---
st.title("💰 Budget Compliance Monitor")
st.caption("Powered by Gemini 2.0 Flash Engine")

# Load and display the data
data = load_data()
st.subheader("Current Spend Overview")
st.dataframe(
    data.style.format({
        "variance_%": "{:.2f}%", 
        "budgeted": "${:,.2f}", 
        "actual": "${:,.2f}",
        "variance": "${:,.2f}"
    })
)

if st.button("🚀 Run AI Compliance Audit"):
    # Filter for any department more than 5% over budget
    overspenders = data[data['variance_%'] > 5.0]
    
    if not overspenders.empty:
        st.divider()
        for _, row in overspenders.iterrows():
            with st.spinner(f"Gemini 2.0 is reviewing {row['department']}..."):
                # Pass data to the AI
                insight = get_ai_insight(
                    row['department'], 
                    row['budgeted'], 
                    row['actual'], 
                    row['variance_%']
                )
                
                # UI Display
                st.warning(f"**{row['department'].upper()} Alert:** {insight}")
                
                # Slack Notification
                slack_msg = f"🚨 *Budget Alert: {row['department'].upper()}*\n*Insight:* {insight}"
                send_slack(slack_msg)
        
        st.success("Audit complete. Insights delivered to Slack.")
    else:
        st.success("✅ All departments are currently within compliant thresholds.")
