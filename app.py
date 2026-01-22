import streamlit as st
import pandas as pd
import requests
import json
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Budget AI Monitor", page_icon="💰")

# --- 2. KEYS & INITIALIZATION ---
try:
    # Ensure these are set in your Streamlit Cloud Secrets
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    SLACK_WEBHOOK = st.secrets["SLACK_WEBHOOK"]
    
    # Updated to 'gemini-1.5-flash-latest' to avoid 404 errors
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest", 
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
        
        # Ensure data types are numeric for calculations
        df['budgeted'] = pd.to_numeric(df['budgeted'], errors='coerce')
        df['actual'] = pd.to_numeric(df['actual'], errors='coerce')
        
        # Calculate Variance
        df['variance'] = df['actual'] - df['budgeted']
        df['variance_%'] = (df['variance'] / df['budgeted']) * 100
        return df
    except FileNotFoundError:
        st.error("🚨 File 'Budget Trigger App.csv' not found. Ensure it is in your GitHub root folder.")
        st.stop()
    except Exception as e:
        st.error(f"Error processing CSV: {e}")
        st.stop()

def get_ai_insight(dept, budgeted, actual, variance_pct):
    """Feeds budget data to Gemini for contextual analysis."""
    prompt = (
        f"Department: {dept}, Budget: {budgeted}, Actual: {actual}, Variance: {variance_pct:.2f}%. "
        "As a financial expert, briefly explain if this overspend is critical or expected. "
        "Provide a 1-sentence recommendation."
    )
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"AI Analysis Error: {str(e)}"

def send_slack(message):
    """Sends the final alert to your Slack channel."""
    try:
        requests.post(SLACK_WEBHOOK, json={"text": message}, timeout=5)
    except Exception as e:
        st.error(f"Failed to send Slack alert: {e}")

# --- 4. MAIN USER INTERFACE ---
st.title("💰 Budget Compliance Monitor")
st.markdown("Monitoring real-time variances and generating AI-powered insights.")

# Load and display the data
data = load_data()
st.subheader("Current Department Spend Status")
st.dataframe(
    data.style.format({"variance_%": "{:.2f}%", "budgeted": "${:,.2f}", "actual": "${:,.2f}"})
)

if st.button("🚀 Run AI Compliance Audit"):
    # Filter for any department more than 5% over budget
    overspenders = data[data['variance_%'] > 5.0]
    
    if not overspenders.empty:
        st.divider()
        for _, row in overspenders.iterrows():
            with st.spinner(f"AI is reviewing {row['department']}..."):
                # Pass cleaned lowercase keys to the AI function
                insight = get_ai_insight(
                    row['department'], 
                    row['budgeted'], 
                    row['actual'], 
                    row['variance_%']
                )
                
                # Show results in the app
                st.warning(f"**{row['department'].upper()} Alert:** {insight}")
                
                # Send the "Ping" to Slack
                slack_msg = f"🚨 *Budget Alert: {row['department'].upper()}*\n*Insight:* {insight}"
                send_slack(slack_msg)
        
        st.success("Audit complete. Alerts sent to Slack.")
    else:
        st.success("✅ All departments are within the 5% threshold.")
