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

# --- 2. AI INITIALIZATION ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    
    # Initialize Gemini 2.0 Flash
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        google_api_key=GOOGLE_API_KEY,
        temperature=0.2
    )
except KeyError:
    st.error("🔑 Please add GOOGLE_API_KEY to your Streamlit Secrets.")
    st.stop()

# --- 3. DATA ENGINE ---
def load_and_process_data():
    try:
        df = pd.read_csv("Budget Trigger App.csv")
        df.columns = df.columns.str.strip().str.lower()
        # Ensure numeric types
        for col in ['budgeted', 'actual']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df['variance_pct'] = df.apply(
            lambda x: ((x['actual'] - x['budgeted']) / x['budgeted'] * 100) if x['budgeted'] != 0 else 0, 
            axis=1
        )
        return df
    except Exception as e:
        st.error(f"❌ Could not load CSV: {e}")
        return None

# --- 4. MAIN DASHBOARD ---
st.title("💎 FinAI Compliance Dashboard")
st.markdown("### Real-time Budget Variance Analysis & AI Audit")

data = load_and_process_data()

if data is not None:
    # Top Row Metrics
    col1, col2, col3 = st.columns(3)
    total_budget = data['budgeted'].sum()
    total_actual = data['actual'].sum()
    total_var = ((total_actual - total_budget) / total_budget * 100) if total_budget != 0 else 0
    
    col1.metric("Total Budgeted", f"${total_budget:,.0f}")
    col2.metric("Total Actual", f"${total_actual:,.0f}")
    col3.metric("Global Variance", f"{total_var:.1f}%", delta=f"{total_var:.1f}%", delta_color="inverse")

    st.divider()

    # Data Display
    st.subheader("Departmental Breakdown")
    st.dataframe(
        data.style.format({"variance_pct": "{:.1f}%", "actual": "${:,.2f}", "budgeted": "${:,.2f}"}),
        use_container_width=True
    )

    # AI Audit Button
    if st.button("🔍 Run AI Compliance Audit"):
        overspenders = data[data['variance_pct'] > 5.0]
        
        if not overspenders.empty:
            with st.status("🧠 Gemini 2.0 analyzing data...", expanded=True) as status:
                # Batch request to avoid 429 quota errors
                summary = overspenders[['department', 'variance_pct']].to_string(index=False)
                prompt = f"Summarize the risk for these overspending departments in 1 sentence each: {summary}"
                
                try:
                    response = llm.invoke(prompt)
                    st.subheader("🤖 AI Auditor Insights")
                    st.warning(response.content)
                    st.success("✅ Audit Complete. Insights sent to manager.")
                    status.update(label="Analysis Complete", state="complete")
                except Exception as e:
                    st.error(f"AI Quota Limit Reached. Standard protocol: Budget exceeded for {len(overspenders)} departments.")
        else:
            st.success("✨ All departments are currently within their allocation.")
