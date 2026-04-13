import os
import json
import sqlite3
import re
import io
import pandas as pd
import streamlit as st
import PyPDF2
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="AgriSense Portal",
    page_icon="🤖",
    layout="wide"
)

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'hr_database.db')
INTENTS_PATH = os.path.join(BASE_DIR, 'hr_intents.json')

# --- Logic Engine ---

class IntentClassifier:
    def __init__(self, intents_file):
        try:
            with open(intents_file, 'r') as f:
                self.intents = json.load(f)['intents']
        except: self.intents = []
    def process(self, text):
        text = text.lower()
        for i in self.intents:
            for p in i['phrases']:
                if p.lower() in text: return i['intent']
        return "unknown"

class HRSystem:
    def __init__(self, db_path):
        self.db_path = db_path
    def _query(self, query, params=(), commit=False, fetchone=False):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
                return cursor.lastrowid
            if fetchone:
                result = cursor.fetchone()
                return dict(result) if result else None
            return [dict(r) for r in cursor.fetchall()]
        except: return None
        finally:
            if 'conn' in locals(): conn.close()
    def get_jobs(self): return self._query("SELECT * FROM jobs") or []
    def get_apps(self, email):
        return self._query("SELECT a.id, a.status, j.title, j.location FROM applications a JOIN jobs j ON a.position_id = j.id WHERE a.email = ?", (email,)) or []
    def apply(self, name, email, job_id):
        return self._query("INSERT INTO applications (name, email, status, position_id) VALUES (?, ?, ?, ?)", (name, email, "Under Review", job_id), commit=True)
    def get_application_status(self, app_id):
        return self._query("SELECT * FROM applications WHERE id = ?", (app_id,), fetchone=True)

# --- Initialization ---
if "init_v3" not in st.session_state:
    st.session_state.email = None
    st.session_state.name = "Guest"
    st.session_state.theme = "Light"
    st.session_state.messages = [{"role": "bot", "content": "👋 **Hello!** I'm your HR AI. Use the button suggestions below for quick answers!"}]
    st.session_state.system = HRSystem(DB_PATH)
    st.session_state.nlu = IntentClassifier(INTENTS_PATH)
    st.session_state.init_v3 = True

def apply_theme(theme):
    if theme == "Dark":
        st.markdown("<style>.stApp { background: #111; color: white; } .stChatMessage { background: #222 !important; border-radius: 10px; } .stButton>button { background: #333 !important; color: white !important; }</style>", unsafe_allow_html=True)
    else:
        st.markdown("<style>.stApp { background: #fafafa; color: #333; } .stChatMessage { background: #fff !important; border: 1px solid #eee; border-radius: 10px; }</style>", unsafe_allow_html=True)

def get_bot_response(prompt):
    intent = st.session_state.nlu.process(prompt)
    if intent == "greet": return "Hello! How can I help you today?"
    if intent == "job_openings": return "You can see all our current openings in the left panel!"
    if intent == "leave_policy": return "Our policy provides 24 days of paid leave per year."
    if intent == "check_status":
        ids = re.findall(r'\d+', prompt)
        if ids:
            status = st.session_state.system.get_application_status(ids[0])
            if status: return f"📋 **Application #{ids[0]} Status:** {status['status']}"
        return "Please provide your Application ID."
    return "I'm your HR assistant! Ask me about jobs or status."

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Control")
    st.session_state.theme = "Dark" if st.toggle("🌙 Dark Mode", value=(st.session_state.theme == "Dark")) else "Light"
    apply_theme(st.session_state.theme)
    st.divider()
    if st.session_state.email:
        st.write(f"Active Profile: **{st.session_state.name}**")
        apps = st.session_state.system.get_apps(st.session_state.email)
        st.metric("Total Applications", len(apps))
        if st.button("Logout"):
            st.session_state.email = None
            st.rerun()
    else:
        res = st.file_uploader("Upload Resume (PDF)", type="pdf")
        if res:
            st.session_state.email = "demo@example.com"
            st.session_state.name = "Shaurya Singh"
            st.rerun()
    st.divider()
    jobs = st.session_state.system.get_jobs()
    if jobs:
        df = pd.DataFrame(jobs)
        st.bar_chart(df['department'].value_counts())

# --- Layout ---
col_main, col_chat = st.columns([1.8, 1])

with col_main:
    st.title("🏢 Career Portal")
    search = st.text_input("🔍 Search roles...")
    filtered = [j for j in jobs if not search or search.lower() in j['title'].lower()]
    for i, job in enumerate(filtered):
        with st.container(border=True):
            st.subheader(job['title'])
            st.caption(f"{job['department']} • {job['location']}")
            if st.button("Apply Now", key=f"apply_{job['id']}_{i}"):
                if not st.session_state.email: st.warning("Upload resume first!")
                else:
                    app_id = st.session_state.system.apply(st.session_state.name, st.session_state.email, job['id'])
                    st.toast(f"Application #{app_id} Sent!", icon="🚀")
                    st.rerun()

with col_chat:
    st.title("💬 AI Guide")
    chat_box = st.container(height=450, border=True)
    for m in st.session_state.messages:
        chat_box.chat_message(m["role"]).markdown(m["content"])
    
    # --- QUICK SUGGESTIONS ---
    st.write("💡 Suggested Actions:")
    s_col1, s_col2 = st.columns(2)
    
    if s_col1.button("📂 View Jobs", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "View job openings"})
        st.session_state.messages.append({"role": "bot", "content": get_bot_response("View job openings")})
        st.rerun()
        
    if s_col2.button("📜 Leave Policy", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "What is the leave policy?"})
        st.session_state.messages.append({"role": "bot", "content": get_bot_response("Leave policy")})
        st.rerun()
        
    s_col3, s_col4 = st.columns(2)
    if s_col3.button("❓ App Status", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "Check status of application"})
        st.session_state.messages.append({"role": "bot", "content": "Please provide your Application ID (e.g. 'Status of 101')."})
        st.rerun()
        
    if s_col4.button("💰 Salary Info", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "Tell me about salaries"})
        st.session_state.messages.append({"role": "bot", "content": "Salaries are credited on the last day of the month. Check your payslip portal for details."})
        st.rerun()

    if prompt := st.chat_input("Type here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "bot", "content": get_bot_response(prompt)})
        st.rerun()
