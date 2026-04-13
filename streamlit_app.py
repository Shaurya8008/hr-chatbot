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
    page_title="AgriSense Elite | Smart HR",
    page_icon="💠",
    layout="wide"
)

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'hr_database.db')
INTENTS_PATH = os.path.join(BASE_DIR, 'hr_intents.json')

# --- Logic Engines ---

class ResumeIntelligence:
    KNOWN_SKILLS = {'python', 'javascript', 'react', 'sql', 'flask', 'django', 'aws', 'docker', 'git', 'java', 'nodejs', 'typescript', 'c++', 'oop', 'machine learning'}
    
    @staticmethod
    def parse_pdf(pdf_bytes):
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            text = "".join([p.extract_text() for p in reader.pages])
            skills = [s for s in ResumeIntelligence.KNOWN_SKILLS if s in text.lower()]
            email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
            email = email_match.group(0) if email_match else "candidate@example.com"
            return {"text": text, "skills": skills, "email": email}
        except: return None

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

# --- Session Initialization ---
if "init_v5" not in st.session_state:
    st.session_state.email = None
    st.session_state.name = "Guest Candidate"
    st.session_state.skills = []
    st.session_state.theme = "Light"
    st.session_state.messages = [{"role": "bot", "content": "👋 **Welcome!** Upload a resume to see your smart job recommendation matches!"}]
    st.session_state.system = HRSystem(DB_PATH)
    st.session_state.interview_mode = False
    st.session_state.interview_step = 0
    st.session_state.init_v5 = True

# --- Theme CSS ---
def apply_theme(theme):
    if theme == "Dark":
        st.markdown("<style>.stApp { background: #0e1117; color: white; } .stChatMessage { background: #161b22 !important; }</style>", unsafe_allow_html=True)
    else:
        st.markdown("<style>.stApp { background: #f8fafc; color: #1e293b; } .stChatMessage { background: #ffffff !important; border: 1px solid #e2e8f0; }</style>", unsafe_allow_html=True)

# --- Interview Questions ---
QUESTIONS = [
    "Tell us about a technical challenge you solved recently.",
    "How do you handle deadlines under pressure?",
    "What interests you about AgriSense?",
    "Describe your experience with the skills listed on your resume."
]

def handle_chat(prompt):
    if st.session_state.interview_mode:
        st.session_state.interview_step += 1
        if st.session_state.interview_step < len(QUESTIONS):
            return {"role": "bot", "content": f"👉 **Question {st.session_state.interview_step+1}:** {QUESTIONS[st.session_state.interview_step]}"}
        st.session_state.interview_mode = False
        return {"role": "bot", "content": "🏁 **Interview Complete!** Great job. We've updated your application profile."}
    
    p = prompt.lower()
    
    # HR Policy & FAQ Support
    if "leave" in p or "policy" in p or "vacation" in p:
        return {"role": "bot", "content": "📅 **Leave Policy:** Employees get 25 days of annual leave. Requests can be submitted through the payroll portal."}
    if "salary" in p or "pay" in p or "bonus" in p:
        return {"role": "bot", "content": "💰 **Compensation:** Salaries are credited on the last working day of the month. Annual bonuses are performance-linked."}
    if "onboarding" in p or "joining" in p:
        return {"role": "bot", "content": "📑 **Onboarding:** Please bring your ID, education certificates, and tax documents on your first day."}
    
    # Smart Status Support
    if "status" in p or "track" in p:
        ids = re.findall(r'\d+', prompt)
        if ids:
            s = st.session_state.system.get_application_status(ids[0])
            if s: return {"role": "bot", "content": f"🎯 **Status for ID #{ids[0]}:** {s['status']}"}
        
        # Auto-detect from session email
        if st.session_state.email:
            apps = st.session_state.system.get_apps(st.session_state.email)
            if apps:
                latest = apps[-1]
                return {"role": "bot", "content": f"📋 **Latest Update:** Your application for **{latest['title']}** is currently **{latest['status']}**."}
        return {"role": "bot", "content": "Please specify your Application ID, or upload your resume to see your history."}
    
    # Smart Matching Support
    if "suggest" in p or "match" in p or "recommend" in p:
        if st.session_state.skills:
            # We already have scored_jobs in the tab scope, but let's re-calculate for the bot
            jobs = st.session_state.system.get_jobs()
            matches = []
            for j in jobs:
                j_skills = set(s.strip().lower() for s in j['skills'].split(','))
                u_skills = set(st.session_state.skills)
                score = int((len(j_skills & u_skills) / max(len(j_skills), 1)) * 100)
                if score > 0: matches.append((j['title'], score))
            
            matches = sorted(matches, key=lambda x: x[1], reverse=True)
            if matches:
                res = "🎯 **Top Recommendations for you:**\n" + "\n".join([f"- **{m[0]}** ({m[1]}% match)" for m in matches[:3]])
                return {"role": "bot", "content": res}
        return {"role": "bot", "content": "Try uploading your resume in the sidebar! I'll then suggest roles matching your unique skills."}
    
    return {"role": "bot", "content": "I'm your HR AI. You can ask about policies, application status, or for job recommendations!"}

# --- Sidebar ---
with st.sidebar:
    st.title("🌐 Smart Portal")
    st.session_state.theme = "Dark" if st.toggle("🌙 Dark Mode", value=(st.session_state.theme == "Dark")) else "Light"
    apply_theme(st.session_state.theme)
    
    st.divider()
    if not st.session_state.email:
        res_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
        if res_file:
            data = ResumeIntelligence.parse_pdf(res_file.read())
            if data:
                st.session_state.email = data['email']
                st.session_state.skills = data['skills']
                st.session_state.name = "Verified Candidate"
                st.balloons()
                st.rerun()
    else:
        st.success(f"Verified: **{st.session_state.email}**")
        if st.button("Logout"):
            st.session_state.email = None
            st.rerun()

    st.divider()
    st.subheader("🏢 Market Summary")
    jobs = st.session_state.system.get_jobs()
    if jobs:
        st.bar_chart(pd.DataFrame(jobs)['department'].value_counts())

# --- Main Layout ---
tab_jobs, tab_profile, tab_chat = st.tabs(["🏢 Job Board", "👤 My Profile", "💬 AI Interview"])

with tab_jobs:
    st.title("💠 Opportunity Engine")
    
    # Matching Engine
    scored_jobs = []
    for j in jobs:
        j_skills = set(s.strip().lower() for s in j['skills'].split(','))
        u_skills = set(st.session_state.skills)
        match_count = len(j_skills & u_skills)
        match_pct = int((match_count / max(len(j_skills), 1)) * 100)
        scored_jobs.append({**j, 'match': match_pct})
    
    scored_jobs = sorted(scored_jobs, key=lambda x: x['match'], reverse=True)
    
    search = st.text_input("🔍 Search roles...", placeholder="e.g. 'Software Engineer'")
    
    for i, job in enumerate(scored_jobs):
        if search and search.lower() not in job['title'].lower(): continue
        
        with st.container(border=True):
            col_info, col_btn = st.columns([4, 1])
            col_info.subheader(job['title'])
            col_info.caption(f"{job['department']} • {job['location']}")
            
            if st.session_state.skills:
                color = "green" if job['match'] > 50 else "orange" if job['match'] > 0 else "grey"
                col_btn.markdown(f":{color}[**{job['match']}% Match**]")
            
            with st.expander("Explore Requirements"):
                st.write(job['description'])
                st.write("**Target Skills:** " + job['skills'])
                if st.session_state.skills:
                    matches = [s for s in job['skills'].split(',') if s.strip().lower() in st.session_state.skills]
                    if matches: st.success(f"Matching Skills: {', '.join(matches)}")
            
            if col_btn.button("Apply", key=f"apply_{job['id']}_{i}", use_container_width=True):
                if not st.session_state.email: st.warning("Upload resume in sidebar!")
                else:
                    app_id = st.session_state.system.apply(st.session_state.name, st.session_state.email, job['id'])
                    st.toast(f"Transmission ID #{app_id} Created!", icon="🚀")
                    st.rerun()

with tab_profile:
    st.title("👤 My Career Profile")
    if not st.session_state.email:
        st.info("Upload a resume in the sidebar to populate your profile.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.write("### Extracted Skills")
            for s in st.session_state.skills:
                st.code(s.upper())
        with c2:
            st.write("### Application History")
            apps = st.session_state.system.get_apps(st.session_state.email)
            for a in apps:
                st.info(f"#{a['id']} - **{a['title']}** ({a['status']})")

with tab_chat:
    st.title("💬 AI Screening & Guidance")
    col_c, col_q = st.columns([2, 1])
    
    with col_c:
        with st.container(height=500, border=True):
            for m in st.session_state.messages:
                st.chat_message(m["role"]).write(m["content"])
        
        if prompt := st.chat_input("Start Interview or Ask Status..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            if "interview" in prompt.lower() and not st.session_state.interview_mode:
                st.session_state.interview_mode = True
                st.session_state.interview_step = -1
            
            resp = handle_chat(prompt)
            st.session_state.messages.append(resp)
            st.rerun()
    
    with col_q:
        st.write("### Quick Actions")
        if st.button("🚀 Start Mock Interview", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "I want to start the interview"})
            st.session_state.interview_mode = True
            st.session_state.interview_step = -1
            resp = handle_chat("start")
            st.session_state.messages.append(resp)
            st.rerun()
        
        st.write("### FAQ Suggestions")
        st.caption("- How many leaves do we get?\n- Check application status\n- Company tech stack")
