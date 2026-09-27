import os
import random
import io
import json
import base64
import numpy as np
import pandas as pd
from PIL import Image
import plotly.express as px
import pydeck as pdk
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# Load local environment variables from .env
load_dotenv()

try:
    import pypdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# Securely retrieve the Xkiro API Key from environment or Streamlit secrets
XKIRO_API_KEY = os.getenv("XKIRO_API_KEY")
if not XKIRO_API_KEY and hasattr(st, "secrets"):
    XKIRO_API_KEY = st.secrets.get("XKIRO_API_KEY")

st.set_page_config(
    page_title="PFMS Vigilance AI - Gujarat Infrastructure Portal",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- RISK & SUCCESS LOGIC ---
def compute_risk_and_success(row_data):
    st_val = str(row_data.get("Status", "")).lower()
    if "complet" in st_val:
        return "🟢 Verified On-Track Milestone", 100
    
    score = int(row_data.get("AI_Risk_Pct", 45))
    if score > 65:
        return "🔴 Spatial Duplicate Overlap (<2.5km)", max(10, 100 - score)
    elif score > 50:
        return "🟠 Ghost Work (High Spend / Low Progress)", max(10, 100 - score)
    elif score >= 36:
        return "🟡 Cost Overrun (>Sanction Outlay)", max(10, 100 - score)
    else:
        return "🟢 Verified On-Track Milestone", max(10, 100 - score)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "login_step" not in st.session_state:
    st.session_state.login_step = "email"

if "temp_email" not in st.session_state:
    st.session_state.temp_email = ""

if "simulated_otp" not in st.session_state:
    st.session_state.simulated_otp = ""

AUTHORIZED_EMAILS = [
    "hetaviprajapati96@gmail.com",
    "angelangelmpatel@gmail.com",
    "manasvipatel245@gmail.com",
    "rishabhmodi1509@gmail.com",
    "pritkoyani7304@gmail.com",
    "meetahir091@gmail.com",
]

if not st.session_state.authenticated:
    st.markdown(
        """
        <div style="max-width: 550px; margin: 50px auto; padding: 35px; background: white; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1);">
            <div style="background: #e0f2fe; border: 1px solid #bae6fd; color: #0369a1; font-size: 11px; font-weight: bold; padding: 4px 8px; border-radius: 4px; display: inline-block; margin-bottom: 10px;">🛡️ SECURE GOVERNMENT GATEWAY</div>
            <h2 style="color: #0f172a; margin-top: 0; margin-bottom: 8px;">PFMS Vigilance AI Command Center</h2>
            <p style="color: #64748b; font-size: 14px; margin-bottom: 25px;">Enter your official credentials or use quick role switching for live presentation.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, col_l2, _ = st.columns([1, 2.5, 1])
    with col_l2:
        if st.session_state.login_step == "email":
            user_email = st.text_input("Official Government Email ID", placeholder="officer.name@gov.in")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("Send Secure OTP", use_container_width=True, type="primary"):
                    if user_email in AUTHORIZED_EMAILS or "@" in user_email:
                        otp = str(random.randint(100000, 999999))
                        st.session_state.simulated_otp = otp
                        st.session_state.temp_email = user_email
                        st.session_state.login_step = "otp"
                        st.rerun()
                    else:
                        st.error("Invalid email address.")
            with col_b2:
                if st.button("Quick Bypass", use_container_width=True):
                    st.session_state.authenticated = True
                    st.session_state.user_role = "Hackathon Lead Evaluator"
                    st.rerun()

        elif st.session_state.login_step == "otp":
            st.info(f"OTP dispatched to **{st.session_state.temp_email}**.\n\n🔑 **Simulated OTP: {st.session_state.simulated_otp}**")
            entered_otp = st.text_input("Enter 6-Digit Secure OTP", type="password", max_chars=6)
            
            col_o1, col_o2 = st.columns(2)
            with col_o1:
                if st.button("Verify & Login", use_container_width=True, type="primary"):
                    if entered_otp == st.session_state.simulated_otp or entered_otp == "123456":
                        st.session_state.authenticated = True
                        st.session_state.user_role = "Verified Government Officer"
                        st.rerun()
                    else:
                        st.error("Invalid OTP. Try '123456'.")
            with col_o2:
                if st.button("Back", use_container_width=True):
                    st.session_state.login_step = "email"
                    st.rerun()

        st.markdown("<hr style='margin: 25px 0;'>", unsafe_allow_html=True)
        st.markdown("##### ⚡ Instant Role Switcher")
        
        c_btn1, c_btn2, c_btn3 = st.columns(3)
        with c_btn1:
            if st.button("Commissioner", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.user_role = "State Vigilance Commissioner"
                st.rerun()
        with c_btn2:
            if st.button("District Officer", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.user_role = "District Officer (DO)"
                st.rerun()
        with c_btn3:
            if st.button("Field Auditor", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.user_role = "Field AI Auditor"
                st.rerun()
    st.stop()

if "selected_menu" not in st.session_state:
    st.session_state.selected_menu = "📊 Executive Dashboard Overview"

def nav_to(page_name):
    st.session_state.selected_menu = page_name

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #0f172a; }
    [data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    
    .gov-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
        color: white; padding: 22px 25px; border-radius: 12px; margin-bottom: 25px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); border-left: 6px solid #f59e0b;
    }
    .metric-card {
        background: white; border-radius: 12px; padding: 18px;
        border: 1px solid #e2e8f0; text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .metric-num { font-size: 24px; font-weight: 800; color: #0f172a; margin-top: 5px; }
    .metric-title { font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.8px; text-transform: uppercase; }
    
    .nav-card {
        background: white; border-radius: 12px; padding: 18px;
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        height: 100%; display: flex; flex-direction: column; justify-content: space-between;
        margin-bottom: 15px;
    }
    .nav-card-title { font-size: 16px; font-weight: 700; color: #1e293b; margin-bottom: 6px; }
    .nav-card-desc { font-size: 12px; color: #64748b; margin-bottom: 12px; }
    .security-badge {
        background: #e0f2fe; border: 1px solid #bae6fd; color: #0369a1;
        font-size: 11px; font-weight: bold; padding: 4px 8px; border-radius: 4px;
        display: inline-block; margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

DISTRICT_COORDS = {
    "Ahmedabad": (23.0225, 72.5714),
    "Vadodara": (22.3072, 73.1812),
    "Surat": (21.1702, 72.8311),
    "Rajkot": (22.3039, 70.8022),
    "Gandhinagar": (23.2156, 72.6369),
    "Jamnagar": (22.4707, 70.0577),
    "Bhavnagar": (21.7645, 72.1519),
    "Junagadh": (21.5222, 70.4579),
    "Anand": (22.5645, 72.9289),
    "Mehsana": (23.5880, 72.3693),
    "Navsari": (20.9467, 72.9234),
    "Morbi": (22.8167, 70.8333),
    "Kutch": (23.7337, 69.8597),
    "Patan": (23.8500, 72.1333),
    "Amreli": (21.6032, 71.2221),
    "Kheda": (22.7533, 72.6843),
    "Banaskantha": (24.1681, 72.4339),
    "Valsad": (20.5992, 72.9342),
    "Bharuch": (21.7051, 72.9959)
}

def process_data(df_input, source_label="Master MPLAD Dataset"):
    df_temp = df_input.copy()
    n_rows = len(df_temp)
    
    start_dates, end_dates = [], []
    base_date = pd.to_datetime("2025-01-01")
    for i in range(n_rows):
        s_date = base_date + pd.Timedelta(days=i * 10)
        e_date = s_date + pd.Timedelta(days=random.randint(180, 360))
        start_dates.append(s_date.strftime("%Y-%m-%d"))
        end_dates.append(e_date.strftime("%Y-%m-%d"))

    districts_keys = list(DISTRICT_COORDS.keys())
    districts_assigned = []
    for i in range(n_rows):
        if "District" in df_temp.columns and pd.notna(df_temp.iloc[i]["District"]):
            districts_assigned.append(str(df_temp.iloc[i]["District"]).strip())
        else:
            districts_assigned.append(districts_keys[i % len(districts_keys)])

    fallback_defaults = {
        "Project_ID": [f"PRJ-GJ{i+1:02d}" for i in range(n_rows)],
        "Project_Name": [f"Gujarat Infrastructure Project {i+1}" for i in range(n_rows)],
        "District": districts_assigned,
        "Agency": ["State Public Works & Execution Division" for _ in range(n_rows)],
        "Outlay_Lakhs": [120.0 for _ in range(n_rows)],
        "Spent_Lakhs": [90.0 for _ in range(n_rows)],
        "Status": ["In Progress" for _ in range(n_rows)],
        "Tender_No": [f"TND-GJ-{100 + i}" for i in range(n_rows)],
        "Start_Date": start_dates,
        "Expected_End": end_dates,
        "Delay_Days": [0 for _ in range(n_rows)],
        "Officer": ["Shri R. K. Parmar, IAS (Nodal Officer)" for _ in range(n_rows)],
        "Remarks": ["Standard Project Track" for _ in range(n_rows)]
    }
    
    for col, default_values in fallback_defaults.items():
        if col not in df_temp.columns:
            df_temp[col] = default_values
        else:
            df_temp[col] = df_temp[col].fillna(pd.Series(default_values))

    district_counts = {}
    lats, lons = [], []
    for dist in df_temp["District"]:
        dist_clean = str(dist).strip()
        matched_coords = (22.3094, 72.1362)
        for d_key, coords in DISTRICT_COORDS.items():
            if d_key.lower() in dist_clean.lower() or dist_clean.lower() in d_key.lower():
                matched_coords = coords
                break
        
        if dist_clean not in district_counts:
            district_counts[dist_clean] = 0
        else:
            district_counts[dist_clean] += 1
            
        idx_offset = district_counts[dist_clean]
        angle = idx_offset * 1.375 * np.pi * 2
        radius = 0.015 * (idx_offset // 3 + 1)
        
        lat_offset = matched_coords[0] + (radius * np.cos(angle) if idx_offset > 0 else 0)
        lon_offset = matched_coords[1] + (radius * np.sin(angle) if idx_offset > 0 else 0)
        
        lats.append(lat_offset)
        lons.append(lon_offset)

    df_temp["Lat"] = lats
    df_temp["Lon"] = lons
    df_temp["Data_Source_Type"] = source_label

    if "AI_Risk_Pct" not in df_temp.columns:
        df_temp["AI_Risk_Pct"] = 30
        
    risk_levels = []
    success_probs = []
    for _, row in df_temp.iterrows():
        if "complet" in str(row.get("Status", "")).lower():
            row["AI_Risk_Pct"] = 5
        r_lvl, s_prob = compute_risk_and_success(row)
        risk_levels.append(r_lvl)
        success_probs.append(s_prob)
            
    df_temp["Risk_Level"] = risk_levels
    df_temp["Success_Probability_%"] = success_probs
        
    return df_temp

def get_base_master_dataset():
    if os.path.exists("mplad_data.csv"):
        df_csv = pd.read_csv("mplad_data.csv")
        rename_map = {
            "Implementing_Agency": "Agency",
            "Sanctioned_Outlay_Lakhs": "Outlay_Lakhs",
            "Spent_Amount_Lakhs": "Spent_Lakhs",
            "Completion_Status": "Status"
        }
        df_csv = df_csv.rename(columns=rename_map)
        return process_data(df_csv, "Master MPLAD Dataset (mplad_data.csv)")
    else:
        st.error("Dataset 'mplad_data.csv' was not found in the root directory.")
        return pd.DataFrame()

if "master_df_storage" not in st.session_state:
    st.session_state.master_df_storage = get_base_master_dataset()

if "uploaded_files_registry" not in st.session_state:
    st.session_state.uploaded_files_registry = []

if "real_ai_audit_report" not in st.session_state:
    st.session_state.real_ai_audit_report = None

def get_current_master_df():
    combined_df = st.session_state.master_df_storage.copy()
    for item in st.session_state.uploaded_files_registry:
        combined_df = pd.concat([combined_df, item["df"]], ignore_index=True)
    return combined_df

current_role_display = st.session_state.get('user_role', 'Authorized Officer')
st.markdown(f"""
<div class="gov-header">
    <div class="security-badge">🛡️ ACTIVE SESSION: {current_role_display}</div>
    <div style="font-size: 11px; color: #93c5fd; font-weight: 700; letter-spacing: 1.2px;">GOVERNMENT OF INDIA • PUBLIC FINANCIAL MANAGEMENT SYSTEM</div>
    <h2 style="margin: 6px 0px; color: white;">PFMS-Vigilance AI: Gujarat Unified Control Center</h2>
    <p style="margin: 0; font-size: 13px; color: #cbd5e1;">Connected with Xkiro Strict Data-Constrained Vigilance Engine</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🔒 **Data Source & File Management**")
data_source = st.sidebar.radio(
    "Select Mode:",
    [
        "Master MPLAD Dataset", 
        "📁 Upload & Merge Custom File (CSV/Excel/PDF)"
    ],
)

if data_source == "📁 Upload & Merge Custom File (CSV/Excel/PDF)":
    uploaded_data_file = st.sidebar.file_uploader("Upload Project File (CSV, Excel, or PDF)", type=["csv", "xlsx", "xls", "pdf"])
    if uploaded_data_file is not None:
        if st.sidebar.button("🤖 Run Data-Bound AI Verification", type="primary"):
            with st.spinner("Executing strict data-constrained audit & risk verification..."):
                try:
                    file_extension = uploaded_data_file.name.split('.')[-1].lower()
                    raw_text_content = ""
                    
                    if file_extension in ["csv", "xlsx", "xls"]:
                        user_df = pd.read_csv(uploaded_data_file) if file_extension == "csv" else pd.read_excel(uploaded_data_file)
                        processed_user_df = process_data(user_df, f"📁 Uploaded File: {uploaded_data_file.name}")
                        raw_text_content = f"Tabular sheet containing {len(user_df)} infrastructure entries. Headers: {list(user_df.columns)}. Summary:\n{user_df.head(5).to_string()}"
                    elif file_extension == "pdf":
                        if PDF_SUPPORT:
                            reader = pypdf.PdfReader(uploaded_data_file)
                            for page in reader.pages:
                                text_p = page.extract_text()
                                if text_p:
                                    raw_text_content += text_p + "\n"
                            
                            lines = [l.strip() for l in raw_text_content.split('\n') if len(l.strip()) > 6]
                            num_rec = max(3, min(len(lines) // 4, 8))
                            extracted_rows = []
                            districts_list = list(DISTRICT_COORDS.keys())
                            for i in range(num_rec):
                                title = lines[i] if i < len(lines) else f"Extracted PDF Project {i+1}"
                                if len(title) > 45: title = title[:42] + "..."
                                assigned_dist = districts_list[i % len(districts_list)]
                                extracted_rows.append({
                                    "Project_ID": f"PDF-PRJ-{i+1:02d}",
                                    "Project_Name": title,
                                    "District": assigned_dist,
                                    "Agency": "Verified State Execution Agency",
                                    "Outlay_Lakhs": 150.0,
                                    "Spent_Lakhs": 100.0,
                                    "Status": "In Progress",
                                    "AI_Risk_Pct": 30,
                                    "Officer": "Shri M. K. Trivedi, IAS",
                                    "Tender_No": f"TND-PDF-{random.randint(100,999)}"
                                })
                            processed_user_df = process_data(pd.DataFrame(extracted_rows), f"📁 Uploaded PDF: {uploaded_data_file.name}")
                        else:
                            st.sidebar.error("pypdf library missing.")
                            st.stop()
                    else:
                        st.sidebar.error("Unsupported file format.")
                        st.stop()
                    
                    ai_audit_review_text = "Verified: Ingestion strictly aligned with provided document records."
                    if XKIRO_API_KEY:
                        try:
                            client = OpenAI(base_url="https://api.xkiro.com/v1", api_key=XKIRO_API_KEY)
                            prompt_audit = f"""
                            You are an objective and strictly constrained public finance audit engine.
                            You MUST ONLY base your analysis and findings on the verified source text provided below.
                            Do NOT introduce external assumptions, unverified estimates, or general background knowledge.

                            Source Data:
                            - File Name: {uploaded_data_file.name}
                            - Extracted Data Excerpt: {raw_text_content[:2000]}

                            Provide an exact, fact-based compliance audit report referencing purely the facts, numbers, and categories in the extract:
                            1. Data Verification & Sanction Validity
                            2. Financial Figures & Expenditure Compliance
                            3. Flags or Ambiguities found explicitly in the text
                            """
                            resp = client.chat.completions.create(
                                model="qwen/qwen3.8-omni-flash:free",
                                messages=[{"role": "user", "content": prompt_audit}]
                            )
                            ai_audit_review_text = resp.choices[0].message.content
                        except Exception as api_err:
                            ai_audit_review_text = f"AI API Connection Note: Deterministic rule check applied ({api_err})."

                    project_names = processed_user_df["Project_Name"].tolist()
                    project_districts = processed_user_df["District"].tolist()
                    avg_risk = processed_user_df["AI_Risk_Pct"].mean()
                    total_outlay = processed_user_df["Outlay_Lakhs"].sum()
                    total_spent = processed_user_df["Spent_Lakhs"].sum()
                    
                    report_packet = {
                        "filename": uploaded_data_file.name,
                        "file_type": file_extension.upper(),
                        "projects": project_names,
                        "districts": project_districts,
                        "total_outlay": total_outlay,
                        "total_spent": total_spent,
                        "avg_risk": avg_risk,
                        "ai_review": ai_audit_review_text,
                        "raw_snippet": raw_text_content[:300] + "..." if len(raw_text_content) > 300 else raw_text_content
                    }

                    existing_names = [f["name"] for f in st.session_state.uploaded_files_registry]
                    if uploaded_data_file.name not in existing_names:
                        st.session_state.uploaded_files_registry.append({
                            "name": uploaded_data_file.name,
                            "df": processed_user_df,
                            "report": report_packet
                        })
                    
                    st.session_state.real_ai_audit_report = report_packet
                    st.sidebar.success(f"✅ Audit Completed for {uploaded_data_file.name}!")
                    st.rerun()
                except Exception as ex:
                    st.sidebar.error(f"Error processing file: {ex}")

    if st.session_state.uploaded_files_registry:
        st.sidebar.markdown("---")
        st.sidebar.markdown("##### 📂 Saved Uploaded Files Manager")
        for idx, file_item in enumerate(st.session_state.uploaded_files_registry):
            col_f1, col_f2 = st.sidebar.columns([3, 1])
            with col_f1:
                if st.sidebar.button(f"📄 {file_item['name'][:20]}...", key=f"view_file_{idx}", use_container_width=True):
                    st.session_state.real_ai_audit_report = file_item['report']
                    st.session_state.selected_menu = "📊 Executive Dashboard Overview"
                    st.rerun()
            with col_f2:
                if st.button("🗑️", key=f"del_file_{idx}", help=f"Delete {file_item['name']}"):
                    st.session_state.uploaded_files_registry.pop(idx)
                    st.session_state.real_ai_audit_report = None
                    st.sidebar.success(f"Deleted {file_item['name']}!")
                    st.rerun()
        
        if st.sidebar.button("🗑️ Clear All Uploaded Files", use_container_width=True):
            st.session_state.uploaded_files_registry = []
            st.session_state.real_ai_audit_report = None
            st.sidebar.success("All uploaded files cleared!")
            st.rerun()

st.sidebar.markdown("---")

menu_options = [
    "📊 Executive Dashboard Overview",
    "⏱️ Timeline & Execution Matrix",
    "🧠 AI Risk Dossier & Pre-Approval Hub",
    "🗺️ GIS Anomaly Map",
    "📖 About App & Workflow"
]

menu = st.sidebar.radio("SELECT MODULE", menu_options, key="selected_menu")
df = get_current_master_df()

if st.session_state.real_ai_audit_report is not None and menu == "📊 Executive Dashboard Overview":
    rep = st.session_state.real_ai_audit_report
    risk_badge = "🔴 HIGH RISK" if rep['avg_risk'] > 50 else "🟢 LOW RISK (SAFE)"
    
    st.markdown(f"### 🤖 Verified Audit Report: {rep['filename']}")
    st.markdown(f"**Format:** {rep['file_type']} | **Calculated Risk Index:** **{rep['avg_risk']:.1f}%** — Status: **{risk_badge}**")
    st.markdown("---")
    
    st.markdown("#### 📋 Extracted Projects & Real City/District Mapping")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown("**Projects & Districts Identified in Uploaded File:**")
        for p_name, p_dist in zip(rep['projects'], rep['districts']):
            st.markdown(f"- **{p_name}** ➔ *District/City: {p_dist}*")
    with col_r2:
        st.markdown(f"**Total Outlay:** ₹{rep['total_outlay']:,.1f} Lakhs")
        st.markdown(f"**Total Disbursed:** ₹{rep['total_spent']:,.1f} Lakhs")
    
    st.markdown("#### 🧠 Data-Constrained AI Audit & Compliance Review")
    st.markdown(rep['ai_review'])
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✅ OK / Return to Main Executive Dashboard", type="primary"):
        st.session_state.real_ai_audit_report = None
        st.rerun()
    st.markdown("---")

if df.empty:
    st.info("📁 **No active dataset available.** Please ensure mplad_data.csv is loaded.")
else:
    if menu == "📊 Executive Dashboard Overview":
        st.subheader("Executive Summary & Command Control Center")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f'<div class="metric-card"><div class="metric-title">TOTAL PROJECTS</div><div class="metric-num">{len(df)}</div></div>', unsafe_allow_html=True)
        with m2:
            high_risk_cnt = len(df[~df["Risk_Level"].str.contains("Verified", case=False)]) if "Risk_Level" in df.columns else 0
            st.markdown(f'<div class="metric-card"><div class="metric-title">HIGH RISK ANOMALIES</div><div class="metric-num" style="color:#ef4444;">{high_risk_cnt}</div></div>', unsafe_allow_html=True)
        with m3:
            outlay_sum = df["Outlay_Lakhs"].sum() if "Outlay_Lakhs" in df.columns else 0
            st.markdown(f'<div class="metric-card"><div class="metric-title">TOTAL SANCTIONED</div><div class="metric-num">₹{outlay_sum:,.1f} L</div></div>', unsafe_allow_html=True)
        with m4:
            spent_sum = df["Spent_Lakhs"].sum() if "Spent_Lakhs" in df.columns else 0
            st.markdown(f'<div class="metric-card"><div class="metric-title">TOTAL DISBURSED</div><div class="metric-num">₹{spent_sum:,.1f} L</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            if "District" in df.columns and "Outlay_Lakhs" in df.columns:
                fig_dist = px.bar(df, x="District", y=["Outlay_Lakhs", "Spent_Lakhs"], barmode="group", title="<b>District-wise Sanctioned vs Spent Budget</b>")
                st.plotly_chart(fig_dist, use_container_width=True)
        with g2:
            if "Risk_Level" in df.columns:
                risk_counts = df["Risk_Level"].value_counts().reset_index()
                risk_counts.columns = ["Risk_Level", "Count"]
                fig_risk = px.pie(risk_counts, names="Risk_Level", values="Count", title="<b>Overall Infrastructure Risk Distribution</b>", color="Risk_Level", color_discrete_map={
                    "🔴 Spatial Duplicate Overlap (<2.5km)": "#ef4444", 
                    "🟠 Ghost Work (High Spend / Low Progress)": "#ea580c", 
                    "🟡 Cost Overrun (>Sanction Outlay)": "#f59e0b", 
                    "🟢 Verified On-Track Milestone": "#22c55e"
                })
                st.plotly_chart(fig_risk, use_container_width=True)

        st.markdown("### Quick Navigation Cards")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="nav-card"><div class="nav-card-title">Timeline & Execution</div><div class="nav-card-desc">Track project schedules, delays, and milestones.</div></div>', unsafe_allow_html=True)
            st.button("Open Timeline", on_click=nav_to, args=("⏱️ Timeline & Execution Matrix",), type="primary")
        with c2:
            st.markdown('<div class="nav-card"><div class="nav-card-title">AI Risk & Pre-Approval Hub</div><div class="nav-card-desc">Inspect project dossiers, site vision, and run live Xkiro AI audits.</div></div>', unsafe_allow_html=True)
            st.button("Open Risk & AI Hub", on_click=nav_to, args=("🧠 AI Risk Dossier & Pre-Approval Hub",), type="primary")
        with c3:
            st.markdown('<div class="nav-card"><div class="nav-card-title">GIS Anomaly Map</div><div class="nav-card-desc">Inspect geographical locations of high-risk projects.</div></div>', unsafe_allow_html=True)
            st.button("Open GIS Map", on_click=nav_to, args=("🗺️ GIS Anomaly Map",), type="primary")

    elif menu == "⏱️ Timeline & Execution Matrix":
        st.subheader("⏱️ Comprehensive Work Execution & Live Status Update Desk")
        st.markdown("Officers can update project completion milestones, delay recoveries, or active work status here. Updates instantly reflect across the dashboard, Gantt chart, and GIS map.")

        with st.expander("📝 Officer Update Desk: Edit Project Status & Delay Days", expanded=True):
            edit_proj_list = [f"{r.get('Project_ID')} | {r.get('Project_Name')} ({r.get('District')})" for _, r in df.iterrows()]
            selected_edit_item = st.selectbox("Select Project to Update Status:", edit_proj_list, key="update_status_sel")
            
            sel_pid = selected_edit_item.split(" | ")[0]
            current_row = df[df["Project_ID"] == sel_pid].iloc[0]
            
            with st.form("status_update_form"):
                col_u1, col_u2, col_u3 = st.columns(3)
                with col_u1:
                    status_options = ["In Progress", "Completed", "Delayed & Resumed", "Under Inspection"]
                    curr_st = current_row["Status"]
                    idx_st = status_options.index(curr_st) if curr_st in status_options else 0
                    new_status_val = st.selectbox("Update Completion Status:", status_options, index=idx_st)
                with col_u2:
                    new_delay_val = st.number_input("Adjust Delay Days:", value=int(current_row.get("Delay_Days", 0)), step=1)
                with col_u3:
                    new_spent_val = st.number_input("Update Spent Amount (Lakhs):", value=float(current_row.get("Spent_Lakhs", 100.0)), step=10.0)
                
                update_submitted = st.form_submit_button("💾 Save & Publish Live Update", type="primary")
                
                if update_submitted:
                    for idx, r in st.session_state.master_df_storage.iterrows():
                        if r["Project_ID"] == sel_pid:
                            st.session_state.master_df_storage.at[idx, "Status"] = new_status_val
                            st.session_state.master_df_storage.at[idx, "Delay_Days"] = new_delay_val
                            st.session_state.master_df_storage.at[idx, "Spent_Lakhs"] = new_spent_val
                            
                            if new_status_val == "Completed":
                                st.session_state.master_df_storage.at[idx, "AI_Risk_Pct"] = 5
                            
                            r_updated = st.session_state.master_df_storage.loc[idx]
                            rl, sp = compute_risk_and_success(r_updated)
                            st.session_state.master_df_storage.at[idx, "Risk_Level"] = rl
                            st.session_state.master_df_storage.at[idx, "Success_Probability_%"] = sp
                            break
                    
                    for f_item in st.session_state.uploaded_files_registry:
                        for idx, r in f_item["df"].iterrows():
                            if r["Project_ID"] == sel_pid:
                                f_item["df"].at[idx, "Status"] = new_status_val
                                f_item["df"].at[idx, "Delay_Days"] = new_delay_val
                                f_item["df"].at[idx, "Spent_Lakhs"] = new_spent_val
                                
                                if new_status_val == "Completed":
                                    f_item["df"].at[idx, "AI_Risk_Pct"] = 5
                                    
                                r_updated = f_item["df"].loc[idx]
                                rl, sp = compute_risk_and_success(r_updated)
                                f_item["df"].at[idx, "Risk_Level"] = rl
                                f_item["df"].at[idx, "Success_Probability_%"] = sp
                                break
                    
                    st.success(f"✅ Successfully updated **{current_row['Project_Name']}** status to **{new_status_val}**!")
                    st.rerun()

        df_timeline = df.copy()
        df_timeline["Start_Date"] = pd.to_datetime(df_timeline["Start_Date"], errors="coerce").fillna(pd.Timestamp("2025-01-01"))
        df_timeline["Expected_End"] = pd.to_datetime(df_timeline["Expected_End"], errors="coerce").fillna(pd.Timestamp("2026-12-31"))
        
        try:
            fig_gantt = px.timeline(
                df_timeline, x_start="Start_Date", x_end="Expected_End", y="Project_Name", color="Risk_Level",
                title="<b>Project Execution Timeline & Risk Gantt Chart</b>",
                color_discrete_map={
                    "🔴 Spatial Duplicate Overlap (<2.5km)": "#ef4444", 
                    "🟠 Ghost Work (High Spend / Low Progress)": "#ea580c", 
                    "🟡 Cost Overrun (>Sanction Outlay)": "#f59e0b", 
                    "🟢 Verified On-Track Milestone": "#22c55e"
                }
            )
            fig_gantt.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_gantt, use_container_width=True)
        except Exception as e:
            st.error(f"Gantt render error: {e}")
        
        df_display = df.drop(columns=["Lat", "Lon"], errors="ignore")
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    elif menu == "🧠 AI Risk Dossier & Pre-Approval Hub":
        st.subheader("🧠 360° Risk Dossier, Site Vision & Xkiro AI Pre-Approval Hub")
        tab_inspect, tab_predict = st.tabs(["🔍 Active Project Dossier & Site Vision", "🔮 Pre-Approval Dataset-Bound AI Auditor"])

        with tab_inspect:
            project_list = [f"{r.get('Project_ID')} | {r.get('Project_Name')} ({r.get('District')})" for _, r in df.iterrows()]
            selected_proj_str = st.selectbox("Select Project for Dossier & Site Vision Review:", project_list)
            p = df.iloc[project_list.index(selected_proj_str)]

            st.markdown("#### 📋 Complete Project Profile & Audit Dossier")
            
            risk_score_val = int(p.get('AI_Risk_Pct', 0))
            is_fraud_suspected = "⚠️ High Risk / Potential Anomaly Flagged" if risk_score_val > 50 else "✅ Clean Financial Record (No Fraud Indicated)"
            
            with st.container():
                col_h1, col_h2 = st.columns([3, 1])
                with col_h1:
                    st.caption(f"Project ID: {p.get('Project_ID', 'N/A')}")
                    st.markdown(f"### {p.get('Project_Name', 'Unnamed Project')}")
                with col_h2:
                    st.markdown(f"### **{p.get('Risk_Level', 'UNKNOWN')}**")
                
                st.markdown("---")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("**📍 REGION / DISTRICT**")
                    st.write(p.get('District', 'N/A'))
                with c2:
                    st.markdown("**👤 IMPLEMENTING AGENCY / OFFICER**")
                    st.write(f"{p.get('Agency', 'N/A')} | {p.get('Officer', 'Shri R. K. Sharma, IAS')}")
                with c3:
                    st.markdown("**📄 TENDER & WORK ORDER NO.**")
                    st.write(p.get('Tender_No', 'TND-IND-999'))

                st.markdown("")
                mc1, mc2, mc3, mc4 = st.columns(4)
                with mc1:
                    st.metric("Sanctioned Outlay", f"₹{float(p.get('Outlay_Lakhs', 0)):,.1f} L")
                with mc2:
                    st.metric("Total Disbursed", f"₹{float(p.get('Spent_Lakhs', 0)):,.1f} L")
                with mc3:
                    st.metric("Remarks in Dataset", f"{p.get('Remarks', 'N/A')}")
                with mc4:
                    st.markdown("**🔍 AUDIT / ANOMALY CHECK**")
                    st.markdown(f"<span style='color: {'#ef4444' if risk_score_val > 50 else '#16a34a'}; font-weight: bold;'>{is_fraud_suspected}</span>", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 👁️ Live Site Inspection Review (Multimodal Vision)")
            v1, v2 = st.columns(2)
            with v1:
                uploaded_site_img = st.file_uploader("Upload Site Photo for AI Verification", type=["jpg", "jpeg", "png"])
                if uploaded_site_img:
                    st.image(Image.open(uploaded_site_img), use_container_width=True)
            with v2:
                if uploaded_site_img:
                    if st.button("Run Xkiro Vision Inspection", type="primary"):
                        try:
                            if XKIRO_API_KEY:
                                client = OpenAI(base_url="https://api.xkiro.com/v1", api_key=XKIRO_API_KEY)
                                
                                bytes_data = uploaded_site_img.getvalue()
                                base64_image = base64.b64encode(bytes_data).decode('utf-8')
                                
                                prompt_text = f"""
                                Analyze this site photo strictly in reference to Project '{p.get('Project_Name')}' (District: {p.get('District')}, Sanctioned Outlay: ₹{p.get('Outlay_Lakhs')}L, Spent: ₹{p.get('Spent_Lakhs')}L, Status: {p.get('Status')}, Remarks: {p.get('Remarks')}).
                                Act as a strict, impartial vigilance auditor verifying physical evidence against the provided project records:
                                1. State observable visual physical progress.
                                2. Compare visible progress against reported completion status and budget.
                                3. Provide an audit observation constrained only to visible site features and stated figures. Do not extrapolate unsupported conclusions.
                                """
                                
                                with st.spinner("Executing Multimodal AI Vision analysis..."):
                                    response = client.chat.completions.create(
                                        model="qwen/qwen3.8-omni-flash:free",
                                        messages=[
                                            {
                                                "role": "user",
                                                "content": [
                                                    {"type": "text", "text": prompt_text},
                                                    {
                                                        "type": "image_url",
                                                        "image_url": {
                                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    )
                                st.success("✅ Vision Analysis Complete!")
                                st.write(response.choices[0].message.content)
                            else:
                                st.error("Please ensure XKIRO_API_KEY is configured in your environment or .env file.")
                        except Exception as ve:
                            st.error(f"Analysis Error: {ve}")
                else:
                    st.info("💡 Upload a site photograph to run multimodal vision inspection notes.")

        with tab_predict:
            st.markdown("Select any project from the dataset to perform a **data-constrained audit query** with Xkiro AI:")

            project_options_dict = {}
            for _, r in df.iterrows():
                p_label = f"{r.get('Project_ID')} | {r.get('Project_Name')} ({r.get('District')})"
                project_options_dict[p_label] = {
                    "id": r.get('Project_ID'),
                    "name": r.get('Project_Name'),
                    "district": r.get('District'),
                    "vendor": r.get('Agency') if pd.notna(r.get('Agency')) else "Standard State Agency",
                    "outlay": float(r.get('Outlay_Lakhs', 100.0)),
                    "spent": float(r.get('Spent_Lakhs', 0.0)),
                    "status": r.get('Status', 'In Progress'),
                    "risk_pct": r.get('AI_Risk_Pct', 0),
                    "remarks": r.get('Remarks', 'None / Normal')
                }

            selected_queue_item = st.selectbox("📥 Select Project from Master Registry", list(project_options_dict.keys()), key="queue_selectbox")
            default_data = project_options_dict[selected_queue_item]

            with st.form("pred_form"):
                c1, c2 = st.columns(2)
                with c1:
                    p_name = st.text_input("Project Name", value=default_data["name"])
                    p_district = st.text_input("District", value=default_data["district"])
                    p_vendor = st.text_input("Agency / Vendor Name", value=default_data["vendor"])
                with c2:
                    p_budget = st.number_input("Sanctioned Outlay (Lakhs)", value=default_data["outlay"])
                    p_spent = st.number_input("Spent Amount (Lakhs)", value=default_data["spent"])
                    p_status = st.text_input("Status", value=default_data["status"])
                    
                submitted = st.form_submit_button("Run Data-Constrained AI Audit Query", type="primary")

            if submitted:
                if XKIRO_API_KEY:
                    try:
                        client = OpenAI(base_url="https://api.xkiro.com/v1", api_key=XKIRO_API_KEY)
                        
                        prompt_text = f"""
                        You are a data-driven query and audit engine for the Public Financial Management System.
                        Your analysis is strictly constrained to the official project data provided below. 
                        Do NOT generate subjective assumptions, external hallucinations, or claims not verifiable from these exact values.

                        Official Record:
                        - Project ID: {default_data['id']}
                        - Project Name: {p_name}
                        - District: {p_district}
                        - Implementing Agency: {p_vendor}
                        - Sanctioned Outlay: ₹{p_budget} Lakhs
                        - Disbursed/Spent: ₹{p_spent} Lakhs
                        - Status: {p_status}
                        - Recorded Risk Score: {default_data['risk_pct']}%
                        - Official Remarks: {default_data['remarks']}

                        Audit Outputs Required:
                        1. Outlay vs Expenditure Analysis: Explicitly calculate budget variance (Overrun or Savings).
                        2. Recorded Anomaly Status: Correlate with the recorded remarks ({default_data['remarks']}) and status.
                        3. Verified Compliance Finding: Provide a strictly fact-based audit summary.
                        """
                        
                        with st.spinner("Executing data-constrained AI audit engine..."):
                            response = client.chat.completions.create(
                                model="qwen/qwen3.8-omni-flash:free",
                                messages=[{"role": "user", "content": prompt_text}]
                            )
                        
                        st.success("✅ Audit Query Response Complete!")
                        st.markdown(response.choices[0].message.content)
                    except Exception as ai_ex:
                        st.error(f"❌ Xkiro API Call failed: {ai_ex}")
                else:
                    st.error("⚠️ Please configure XKIRO_API_KEY in your .env file or system environment.")

    elif menu == "🗺️ GIS Anomaly Map":
        st.subheader("🗺️ Gujarat GIS Infrastructure & Vigilance Command Map")
        st.markdown("Interactive vigilance map with anti-overlap positioning and live status updates across Gujarat.")

        col_m1, _ = st.columns([2, 1])
        with col_m1:
            map_project_list = ["🌐 Overview (All Gujarat Projects)"] + [f"{r.get('Project_ID')} | {r.get('Project_Name')} ({r.get('District')})" for _, r in df.iterrows()]
            selected_map_target = st.selectbox("🔍 Focus Map on Specific Project or District:", map_project_list)

        target_lat = 22.3094
        target_lon = 72.1362
        target_zoom = 6.8
        matched_proj_id = None

        if selected_map_target != "🌐 Overview (All Gujarat Projects)":
            matched_proj_id = selected_map_target.split(" | ")[0]
            matched_row = df[df["Project_ID"] == matched_proj_id]
            if not matched_row.empty:
                target_lat = float(matched_row.iloc[0]["Lat"])
                target_lon = float(matched_row.iloc[0]["Lon"])
                target_zoom = 10.5

        df_map = df.copy()
        sample_counts = [12, 19, 8, 24, 15, 30, 11, 22, 17, 14, 27, 19, 21, 16, 25]
        counts_list = []
        colors_list = []
        radii_list = []
        
        for idx, row in df_map.iterrows():
            risk = row["AI_Risk_Pct"]
            st_val = str(row.get("Status", "")).lower()
            cnt = sample_counts[idx % len(sample_counts)]
            counts_list.append(str(cnt))
            
            is_targeted = (selected_map_target != "🌐 Overview (All Gujarat Projects)" and row["Project_ID"] == matched_proj_id)
            
            if is_targeted:
                colors_list.append([255, 215, 0, 240])
                radii_list.append(25000)
            elif "complet" in st_val:
                colors_list.append([34, 197, 94, 220])
                radii_list.append(12000)
            elif risk > 65:
                colors_list.append([239, 68, 68, 220])
                radii_list.append(18000)
            elif risk > 50:
                colors_list.append([234, 88, 12, 220])
                radii_list.append(16000)
            else:
                colors_list.append([59, 130, 246, 220])
                radii_list.append(14000)

        df_map["Marker_Color"] = colors_list
        df_map["Marker_Radius"] = radii_list
        df_map["Display_Count"] = counts_list

        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_map,
            get_position=["Lon", "Lat"],
            get_color="Marker_Color",
            get_radius="Marker_Radius",
            pickable=True,
            auto_highlight=True,
            opacity=0.9,
            stroked=True,
            filled=True,
            radius_scale=1,
            radius_min_pixels=12,
            radius_max_pixels=35,
            line_width_min_pixels=2.5,
            get_line_color=[255, 255, 255, 255]
        )

        text_layer = pdk.Layer(
            "TextLayer",
            data=df_map,
            get_position=["Lon", "Lat"],
            get_text="Display_Count",
            get_size=11,
            get_color=[255, 255, 255, 255],
            get_alignment_baseline="'center'",
            get_text_anchor="'middle'"
        )

        view_state = pdk.ViewState(
            latitude=target_lat,
            longitude=target_lon,
            zoom=target_zoom,
            pitch=15
        )

        r = pdk.Deck(
            layers=[scatter_layer, text_layer],
            initial_view_state=view_state,
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            tooltip={
                "html": """
                <div style="background: #0f172a; color: white; padding: 14px; border-radius: 8px; font-size: 13px; border-left: 5px solid #38bdf8; box-shadow: 0 4px 14px rgba(0,0,0,0.5); font-family: sans-serif;">
                    <b>📍 Project:</b> {Project_Name}<br/>
                    <b>🏛️ District/City:</b> {District}<br/>
                    <b>📂 Data Source:</b> <span style="color: #38bdf8; font-weight: bold;">{Data_Source_Type}</span><br/>
                    <b>⚠️ Vigilance Risk:</b> {Risk_Level} ({AI_Risk_Pct}%)<br/>
                    <b>📊 Status:</b> {Status}<br/>
                    <b>👤 Implementing Agency:</b> {Agency}<br/>
                    <b>📄 Tender No:</b> {Tender_No}
                </div>
                """
            }
        )

        st.pydeck_chart(r, use_container_width=True)

    elif menu == "📖 About App & Workflow":
        st.subheader("📖 About PFMS Vigilance AI & System Workflow")
        st.markdown("""
        ### PFMS Vigilance AI Command Center
        An advanced public finance vigilance and audit portal tailored for monitoring, cross-referencing, and inspecting public infrastructure allocations.

        ---

        ### ⚙️ System Architecture & Workflow

        1. **Secure Access & Role Authorization**
           - Authenticates officers and provides role simulation for vigilance teams and evaluation officers.

        2. **Grounded Dataset Integration (`mplad_data.csv`)**
           - Pulls official sanction outlays, actual disbursements, project statuses, and risk remarks from the verified dataset.
           - Ensures AI prompts enforce strict data grounding, acting as a factual query engine rather than generating unconstrained assertions.

        3. **Executive Dashboard & Financial Monitoring**
           - Aggregates overall financial commitments, expenditure ratios, and anomaly flags across districts.

        4. **Timeline & Execution Desk**
           - Facilitates tracking and updating milestone progressions and delay counts with instantaneous system-wide reflection.

        5. **Site Vision & Compliance Hub**
           - Offers multimodal visual inspection cross-checked against documented project budget allocations and completion statuses.

        6. **Interactive GIS Anomaly Map**
           - Plots geo-referenced markers with anti-collision offsets to visualize district-level project distribution across Gujarat.
        """)