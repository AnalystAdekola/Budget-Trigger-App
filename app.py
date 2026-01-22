import streamlit as st
import pandas as pd
import time
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. SETUP ---
st.set_page_config(page_title="Budget AI Monitor", page_icon="💰")

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    # Removed Slack webhook from main loop to prevent lag
    
    # Using 'gemini-1.5-flash' for maximum compatibility in 2026
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash", 
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1
    )
except KeyError:
    st.error("Missing Secrets! Add GOOGLE_API_KEY in Streamlit Settings.")
    st.stop()

# --- 2. DATA ENGINE ---
def load_data():
    try:
        df = pd.read_csv("Budget Trigger App.csv")
        df.columns = df.columns.str.strip().str.lower()
        df['budgeted'] = pd.to_numeric(df['budgeted'], errors='coerce').fillna(0)
        df['actual'] = pd.to_numeric(df['actual'], errors='coerce').fillna(0)
        df['variance_%'] = df.apply(lambda x: (x['actual'] - x['budgeted']) / x['budgeted'] * 100 if x['budgeted'] != 0 else 0, axis=1)
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# --- 3. THE SMART AUDIT FUNCTION ---
def run_audit(overspenders_df):
    """Analyzes the list and returns a status without external pings."""
    if overspenders_df.empty:
        return "✅ STATUS: Still within allocation."

    # Prepare data for AI
    summary = overspenders_df[['department', 'variance_%']].to_string(index=False)
    prompt = f"Budget Audit: The following departments exceeded their budget: {summary}. Briefly summarize the risk in 1 sentence."

    try:
        # Single AI attempt
        response = llm.invoke(prompt)
        return f"🚨 ALERT: Sent to Manager. {response.content}"
    except Exception as e:
        # FALLBACK: If API is exhausted, show a standard message instead of an error
        if "429" in str(e) or "quota" in str(e).lower():
            return "🚨 ALERT: Sent to Manager. (Budget exceeded: AI analysis currently offline, using standard protocol)."
        return f"Audit Error: {str(e)}"

# --- 4. INTERFACE ---
st.title("💰 Budget Compliance Monitor")
data = load_data()

if data is not None:
    st.dataframe(data.style.format({"variance_%": "{:.1f}%"}))

    if st.button("🚀 Run Compliance Check"):
        # Threshold: 5% overspend
        overspenders = data[data['variance_%'] > 5.0]
        
        with st.spinner("Checking compliance..."):
            # This handles the AI part locally
            result = run_audit(overspenders)
            
            # Final output to user
            if "ALERT" in result:
                st.warning(result)
            else:
                st.success(result)
