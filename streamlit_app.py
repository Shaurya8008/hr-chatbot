import os
import json
import sqlite3
import re
import io
import pandas as pd
import streamlit as st
import PyPDF2

# --- Page Configuration ---
st.set_page_config(
    page_title="AgriSense HR Portal",
    page_icon="🏢",
    layout="wide"
)

# --- Configuration & Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'hr_database.db')
INTENTS_PATH = os.path.join(BASE_DIR, 'hr_intents.json')

# --- Database & Logic Engine ---

class HRSystem:
    def __init__(self, db_path):
        self.db_path = db_path

    def _query(self, query, params=(), fetchone=False, commit=False):
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
            else:
                result = cursor.fetchall()
                return [dict(r) for r in result]
        except Exception as e:
            st.error(f"System Error: {e}")
            return None
        finally:
            if 'conn' in locals(): conn.close()

    def get_all_jobs(self):
        return self._query("SELECT * FROM jobs")

    def get_applications_by_email(self, email):
        return self._query("""
            SELECT a.id, a.status, j.title, j.location 
            FROM applications a 
            JOIN jobs j ON a.position_id = j.id 
            WHERE a.email = ?
        """, (email,))

    def create_app(self, name, email, job_id):
        return self._query(
            "INSERT INTO applications (name, email, status, position_id) VALUES (?, ?, ?, ?)",
            (name, email, "Under Review", job_id),
            commit=True
        )

# --- UI Sidebar (Global State & Dashboard) ---

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "bot", "content": "Welcome! I'm your HR Partner. Upload your resume to get started or browse jobs below."}]
    st.session_state.user_email = None
    st.session_state.candidate_name = "Candidate"
    st.session_state.system = HRSystem(DB_PATH)

with st.sidebar:
    st.title("👤 Candidate Portal")
    if st.session_state.user_email:
        st.success(f"Loggend in as: {st.session_state.user_email}")
        
        # Dashboard Stats
        apps = st.session_state.system.get_applications_by_email(st.session_state.user_email)
        st.metric("Total Applications", len(apps))
        
        if apps:
            st.write("### Recent Applications")
            for a in apps:
                with st.expander(f"#{a['id']} - {a['title']}"):
                    st.write(f"📍 {a['location']}")
                    st.info(f"Status: {a['status']}")
        
        if st.button("Logout"):
            st.session_state.user_email = None
            st.rerun()
    else:
        st.warning("Upload resume to login")
        resume = st.file_uploader("Upload Resume (PDF)", type="pdf")
        if resume:
            # Mock Parsing for speed
            st.session_state.user_email = "shauryasin8008@gmail.com" # Mocking for this session
            st.session_state.candidate_name = "Shaurya Singh"
            st.balloons()
            st.rerun()

    st.divider()
    st.subheader("📊 Hiring Trends")
    all_jobs = st.session_state.system.get_all_jobs()
    if all_jobs:
        df = pd.DataFrame(all_jobs)
        dept_counts = df['department'].value_counts()
        st.bar_chart(dept_counts)

# --- Main Page Layout ---

col1, col2 = st.columns([2, 1])

with col1:
    st.title("🏢 Career Opportunities")
    
    # Visual Filters
    f_col1, f_col2 = st.columns(2)
    search = f_col1.text_input("🔍 Search roles (e.g. 'Engineer')")
    dept_filter = f_col2.selectbox("📁 Department", ["All"] + sorted(list(set(j['department'] for j in all_jobs))))
    
    # Filter Logic
    display_jobs = all_jobs
    if search:
        display_jobs = [j for j in display_jobs if search.lower() in j['title'].lower() or search.lower() in j['description'].lower()]
    if dept_filter != "All":
        display_jobs = [j for j in display_jobs if j['department'] == dept_filter]

    st.write(f"Showing {len(display_jobs)} results")
    
    for i, job in enumerate(display_jobs):
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.subheader(job['title'])
            c1.caption(f"{job['department']} • {job['location']}")
            
            with st.expander("View Details & Requirements"):
                st.write(job['description'])
                st.write("**Required Skills:**")
                st.write(", ".join(job['skills'].split(',')))
            
            if c2.button("Apply", key=f"apply_btn_{job['id']}"):
                if not st.session_state.user_email:
                    st.error("Please upload your resume in the sidebar first!")
                else:
                    app_id = st.session_state.system.create_app(st.session_state.candidate_name, st.session_state.user_email, job['id'])
                    st.toast(f"Application #{app_id} submitted for {job['title']}!", icon='🚀')
                    st.rerun()

with col2:
    st.title("💬 HR Chat")
    chat_container = st.container(height=500)
    
    for m in st.session_state.messages:
        chat_container.chat_message(m["role"]).markdown(m["content"])
    
    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Simple Logic
        if "policy" in prompt.lower():
            res = "Our annual leave policy provides 24 days per year. It's awesome!"
        elif "status" in prompt.lower():
            if st.session_state.user_email:
                res = f"You have {len(st.session_state.system.get_applications_by_email(st.session_state.user_email))} active applications. Check your sidebar dashboard!"
            else:
                res = "I don't know who you are yet! Please upload your resume."
        else:
            res = "I'm still learning! Try asking about 'policies' or 'application status'."
            
        st.session_state.messages.append({"role": "bot", "content": res})
        st.rerun()
