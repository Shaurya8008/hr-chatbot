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
    page_title="AgriSense Elite | Smart Chat",
    page_icon="🤖",
    layout="wide"
)

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'hr_database.db')
INTENTS_PATH = os.path.join(BASE_DIR, 'hr_intents.json')

# --- Success Dialog ---
@st.dialog("🚀 Application Submitted Successfully!")
def show_success_dialog(app_id, job_title):
    st.balloons()
    st.markdown(f"### Congratulations! 🎊")
    st.write(f"Your application for **{job_title}** has been successfully transmitted to our HR team.")
    st.info(f"**Application Reference ID:** #{app_id}")
    st.write("---")
    st.write("What would you like to do next?")
    col1, col2 = st.columns(2)
    if col1.button("Start Mock Interview", use_container_width=True):
        st.session_state.interview_mode = True
        st.session_state.interview_step = -1
        st.rerun()
    if col2.button("Browse More Jobs", use_container_width=True):
        st.rerun()

# --- Logic Engines ---
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
    def apply(self, name, email, job_id):
        return self._query("INSERT INTO applications (name, email, status, position_id) VALUES (?, ?, ?, ?)", (name, email, "Under Review", job_id), commit=True)
    def get_application_status(self, app_id):
        return self._query("SELECT * FROM applications WHERE id = ?", (app_id,), fetchone=True)
    def get_job_by_id(self, job_id):
        return self._query("SELECT * FROM jobs WHERE id = ?", (job_id,), fetchone=True)
    def get_apps(self, email):
        return self._query("SELECT a.id, a.status, j.title, j.location FROM applications a JOIN jobs j ON a.position_id = j.id WHERE a.email = ?", (email,)) or []

# --- Initialization ---
if "init_v7" not in st.session_state:
    st.session_state.email = None
    st.session_state.name = "Guest"
    st.session_state.theme = "Light"
    st.session_state.messages = [{"role": "bot", "content": "👋 **Hi! I'm your HR Assistant.** Upload your resume to start applying!"}]
    st.session_state.system = HRSystem(DB_PATH)
    st.session_state.interview_mode = False
    st.session_state.interview_step = 0
    st.session_state.init_v7 = True

def apply_theme(theme):
    if theme == "Dark":
        st.markdown("<style>.stApp { background: #0e1117; color: white; } .stChatMessage { background: #161b22 !important; border-radius:15px; }</style>", unsafe_allow_html=True)
    else:
        st.markdown("<style>.stApp { background: #fff; color: #1e293b; } .stChatMessage { background: #f8fafc !important; border: 1px solid #e2e8f0; border-radius:15px; }</style>", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Control")
    st.session_state.theme = "Dark" if st.toggle("🌙 Dark Mode", value=(st.session_state.theme == "Dark")) else "Light"
    apply_theme(st.session_state.theme)
    if not st.session_state.email:
        res = st.file_uploader("Upload Profile (PDF)", type="pdf")
        if res:
            st.session_state.email = "candidate@example.com"
            st.session_state.name = "Shaurya Singh"
            st.rerun()
    else:
        st.success(f"Verified: **{st.session_state.email}**")
        if st.button("Logout"):
            st.session_state.email = None
            st.rerun()

# --- Tabs ---
tab_chat, tab_jobs = st.tabs(["💬 AI Assistant", "🏢 Job Board"])

with tab_chat:
    st.title("🤖 Chat with HR AI")
    box = st.container(height=450, border=True)
    for m in st.session_state.messages: box.chat_message(m["role"]).write(m["content"])
    
    # Quick Commands
    cols = st.columns(3)
    if cols[0].button("🏠 WFH Policy"):
        st.session_state.messages.append({"role": "user", "content": "What is the WFH policy?"})
        st.session_state.messages.append({"role": "bot", "content": "We offer a hybrid policy: 2 days WFH per week!"})
        st.rerun()
    if cols[1].button("⏰ Office Hours"):
        st.session_state.messages.append({"role": "user", "content": "What are the office hours?"})
        st.session_state.messages.append({"role": "bot", "content": "Our hours are 9 AM to 6 PM, Mon-Fri."})
        st.rerun()
    if cols[2].button("❓ Check Status"):
        st.session_state.messages.append({"role": "user", "content": "Check application status"})
        st.session_state.messages.append({"role": "bot", "content": "Type 'Status of [ID]' to check!"})
        st.rerun()

    if prompt := st.chat_input("Type here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Basic logic
        if "apply" in prompt.lower():
            ids = re.findall(r'\d+', prompt)
            if ids and st.session_state.email:
                job = st.session_state.system.get_job_by_id(ids[0])
                if job:
                    app_id = st.session_state.system.apply(st.session_state.name, st.session_state.email, ids[0])
                    show_success_dialog(app_id, job['title'])
                    st.session_state.messages.append({"role": "bot", "content": f"✅ Applied for {job['title']} (ID #{app_id})"})
                    st.rerun()
                else: st.session_state.messages.append({"role": "bot", "content": "Job not found."})
            else: st.session_state.messages.append({"role": "bot", "content": "Please upload resume and specify Job ID (e.g. 'Apply 101')."})
        else:
            st.session_state.messages.append({"role": "bot", "content": "I'm processing your query..."})
        st.rerun()

with tab_jobs:
    jobs = st.session_state.system.get_jobs()
    for job in jobs:
        with st.container(border=True):
            st.subheader(f"#{job['id']} - {job['title']}")
            if st.button("Apply Now", key=f"btn_{job['id']}"):
                if not st.session_state.email: st.error("Upload resume first!")
                else:
                    app_id = st.session_state.system.apply(st.session_state.name, st.session_state.email, job['id'])
                    show_success_dialog(app_id, job['title'])
                    st.rerun()
