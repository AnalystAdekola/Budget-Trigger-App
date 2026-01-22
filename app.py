import streamlit as st
import pandas as pd
import requests
import time
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. SETTINGS ---
st.set_page_config(page_title="Budget AI Monitor", page_icon="💰")

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    SLACK_WEBHOOK = st.secrets["SLACK_WEBHOOK"]
    
    # Using Flash-Lite for HIGHER QUOTA limits in 2026
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite-preview", 
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1
    )
except KeyError:
    st.error("Setup Error: Add GOOGLE_API_KEY and SLACK_WEBHOOK to Streamlit Secrets.")
    st.stop()

# --- 2. DATA ENGINE ---
def load_and_clean_data():
    try:
        df = pd.read_csv("Budget Trigger App.csv")
        df.columns = df.columns.str.strip().str.lower()
        # Convert to numbers and handle missing values
        for col in ['budgeted', 'actual']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Calculate Variance
        df['variance_amt'] = df['actual'] - df['budgeted']
        df['variance_pct'] = df.apply(
            lambda x: (x['variance_amt'] / x['budgeted'] * 100) if x['budgeted'] != 0 else 0, 
            axis=1
        )
        return df
    except Exception as e:
        st.error(f"CSV Error: Ensure 'Budget Trigger App.csv' is in your folder. {e}")
        return None

# --- 3. THE RESILIENT AI CALL ---
def get_ai_analysis(overspenders_df):
    """Sends one batch request with a forced cooling period for 429 errors."""
    summary_text = ""
    for _, row in overspenders_df.iterrows():
        summary_text += f"- {row['department']}: Spent ${row['actual']:,.2f} vs Budget ${row['budgeted']:,.2f} ({row['variance_pct']:.1f}% over)\n"

    prompt = f"""
    Act as a Corporate Controller. Analyze these overspending departments:
    {summary_text}
    
    For each, provide a 1-sentence 'Action Item'. 
    Format: [DEPT NAME]: [Your 1-sentence advice]
    """

    for attempt in range(3): # Try 3 times
        try:
            response = llm.invoke(prompt)
            return response.content
        except Exception as e:
            if "429" in str(e):
                wait_time = 15 * (attempt + 1)
                st.warning(f"Quota reached. Sleeping for {wait_time}s to reset limit...")
                time.sleep(wait_time)
            else:
                return f"⚠️ AI analysis skipped due to technical limit: {str(e)}"
    
    return "❌ API Quota exhausted for the hour. Please try again in 60 seconds."

# --- 4. THE INTERFACE ---
st.title("💰 Budget Compliance Monitor")
st.info("Status: Connected to Gemini 2.0 Flash-Lite (High Quota Mode)")

data = load_and_clean_data()

if data is not None:
    # Highlight overspenders in the table
    st.dataframe(data.style.format({"variance_pct": "{:.1f}%", "actual": "${:,.2f}", "budgeted": "${:,.2f}"}))

    if st.button("🚀 Run AI Audit"):
        overspenders = data[data['variance_pct'] > 5.0]
        
        if not overspenders.empty:
            with st.spinner("Wait... AI is cooling down between requests..."):
                analysis = get_ai_analysis(overspenders)
                
                st.subheader("AI Controller's Report")
                st.markdown(analysis)
                
                # Slack Notification
                try:
                    requests.post(SLACK_WEBHOOK, json={"text": f"🚨 *Budget Audit Report:*\n{analysis}"})
                    st.success("Report pushed to Slack.")
                except:
                    st.error("Slack notification failed, but AI analysis is complete above.")
        else:
            st.success("✅ All departments are compliant.")
