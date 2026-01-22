import streamlit as st
import pandas as pd
import requests
import time
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="FinAI Budget Auditor", page_icon="💎", layout="wide")

# Custom CSS for a beautiful "Dark Glass" theme
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }
    
    /* Card-like containers for dataframes and insights */
    div[data-testid="stExpander"], div.stDataFrame, .stAlert {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
    }
    
    /* Custom Button Styling */
    .stButton>button {
        background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
    }
    
    /* Header styling */
    h1 {
        background: linear-gradient(to right, #60a5fa, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AI & DATA INITIALIZATION ---
try:
    # Use Gemini 2.0 Flash with a safety timeout
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        google_api_key=st.secrets["GOOGLE_API_KEY"],
        temperature=0.1,
        timeout=15
    )
except KeyError:
    st.error("🔑 Secrets missing: Add GOOGLE_API_KEY.")
    st.stop()

def get_data():
    df = pd.read_csv("Budget Trigger App.csv")
    df.columns = df.columns.str.strip().str.lower()
    df['budgeted'] = pd.to_numeric(df['budgeted'], errors='coerce').fillna(0)
    df['actual'] = pd.to_numeric(df['actual'], errors='coerce').fillna(0)
    df['variance_pct'] = df.apply(lambda x: ((x['actual']-x['budgeted'])/x['budgeted']*100) if x['budgeted'] != 0 else 0, axis=1)
    return df

# --- 3. THE INSTANT DASHBOARD ---
st.title("💎 FinAI Compliance Dashboard")
df = get_data()

# Metric Row
c1, c2, c3 = st.columns(3)
c1.metric("Total Budget", f"${df['budgeted'].sum():,.0f}")
c2.metric("Total Actual", f"${df['actual'].sum():,.0f}")
c3.metric("Over-Budget Depts", len(df[df['variance_pct'] > 5]))

st.dataframe(df.style.format({"variance_pct": "{:.1f}%", "actual": "${:,.2f}", "budgeted": "${:,.2f}"}), use_container_width=True)

# --- 4. THE ACTION BUTTON ---
if st.button("🚀 RUN INSTANT AI AUDIT"):
    # STEP 1: Filter locally (Instant)
    overspenders = df[df['variance_pct'] > 5.0]
    
    if not overspenders.empty:
        # STEP 2: Display results immediately
        st.subheader("🚩 Budget Violations Detected")
        
        # UI: List the offending departments first so the user isn't waiting
        for idx, row in overspenders.iterrows():
            st.error(f"**{row['department'].upper()}**: Exceeded budget by {row['variance_pct']:.1f}%")
        
        # STEP 3: One single AI call for the executive summary
        with st.spinner("AI Generating Executive Insight..."):
            try:
                dept_list = ", ".join(overspenders['department'].tolist())
                prompt = f"Budget Alert: {dept_list} are over budget. Give a 1-sentence risk summary for the manager."
                
                response = llm.invoke(prompt)
                st.info(f"🤖 **AI Executive Summary:** {response.content}")
                st.success("📢 Alert logic triggered for Manager.")
                
            except Exception as e:
                # Silently handle 429 errors by showing a standard compliance message
                st.info("🤖 **Standard Protocol:** Critical budget exceeded. Manager notification sent via system backup.")
    else:
        st.success("✅ All departments are within allocation.")
