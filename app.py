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
    
    # max_retries helps, but we will also add manual wait logic
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        google_api_key=GOOGLE_API_KEY,
        temperature=0,
        max_retries=3 
    )
except KeyError:
    st.error("Add GOOGLE_API_KEY and SLACK_WEBHOOK to Streamlit Secrets.")
    st.stop()

# --- 2. THE RESILIENT BRAIN ---
def get_batch_ai_insights(overspenders_df):
    """Analyzes all departments in one call with auto-retry on 429 errors."""
    summary = overspenders_df[['department', 'variance_%']].to_string(index=False)
    
    prompt = f"""
    Review these overspending departments:
    {summary}
    
    Provide a 1-sentence risk assessment for each. 
    Format: DEPT_NAME: Insight text
    """
    
    # Manual Retry Loop for 2026 Quota Limits
    for attempt in range(3):
        try:
            response = llm.invoke(prompt)
            return response.content
        except Exception as e:
            if "429" in str(e):
                st.warning(f"Quota hit. Retrying in {5 + attempt * 5}s...")
                time.sleep(5 + attempt * 5) # Wait longer each time
            else:
                return f"AI Analysis Error: {str(e)}"
    
    return "AI busy. Please wait 1 minute before clicking again."

# --- 3. DATA ENGINE ---
def load_data():
    try:
        df = pd.read_csv("Budget Trigger App.csv")
        df.columns = df.columns.str.strip().str.lower()
        df['budgeted'] = pd.to_numeric(df['budgeted'], errors='coerce').fillna(0)
        df['actual'] = pd.to_numeric(df['actual'], errors='coerce').fillna(0)
        df['variance_%'] = df.apply(lambda x: (x['actual'] - x['budgeted']) / x['budgeted'] * 100 if x['budgeted'] != 0 else 0, axis=1)
        return df
    except Exception as e:
        st.error(f"CSV Error: {e}")
        st.stop()

# --- 4. UI ---
st.title("💰 Budget Compliance Monitor")
data = load_data()
st.dataframe(data.style.format({"variance_%": "{:.2f}%"}))

if st.button("🚀 Run AI Audit"):
    overspenders = data[data['variance_%'] > 5.0]
    
    if not overspenders.empty:
        with st.status("🤖 AI is thinking...", expanded=True) as status:
            st.write("Reviewing budget variances...")
            full_insight = get_batch_ai_insights(overspenders)
            
            st.info("### AI Audit Results")
            st.markdown(full_insight)
            
            # Send to Slack
            requests.post(SLACK_WEBHOOK, json={"text": f"📊 *New Budget Audit:*\n{full_insight}"})
            status.update(label="Audit Complete!", state="complete")
    else:
        st.success("All budgets compliant.")
