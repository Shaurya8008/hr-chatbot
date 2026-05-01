import os, json, sqlite3, re, io, time
import pandas as pd
import streamlit as st
import PyPDF2

from jobs_api import search_jobs, rank_jobs_for_profile, extract_skills_from_description
from application_helper import (
    parse_resume_text, extract_skills, rank_jobs, extract_key_requirements,
    generate_resume_summary, generate_cold_email, generate_cover_letter,
    generate_skill_gap_analysis, generate_follow_up_email, detect_job_bias,
    generate_culture_fit_questions, generate_salary_negotiation_script,
    generate_onboarding_plan, generate_fit_explanation,
)

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_DIR, 'hr_database.db')
INT_PATH  = os.path.join(BASE_DIR, 'hr_intents.json')

st.set_page_config(
    page_title="TalentAI — AI Job Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False  # Default to light for readability

# ─────────────────────────────────────────────
#  PREMIUM CSS — Glassmorphism Light / Dark
# ─────────────────────────────────────────────
def inject_theme(dark: bool):
    if dark:
        bg       = "#0f172a"
        bg2      = "#1e293b"
        card_bg  = "rgba(30, 41, 59, 0.85)"
        card_bdr = "rgba(99, 102, 241, 0.2)"
        glass_bg = "rgba(30, 41, 59, 0.7)"
        text     = "#f1f5f9"   # brighter white for readability
        sub      = "#cbd5e1"   # lighter subtext
        accent   = "#818cf8"   # brighter indigo
        accent2  = "#a78bfa"
        chip_bg  = "rgba(99, 102, 241, 0.15)"
        chip_bdr = "rgba(99, 102, 241, 0.3)"
        chip_clr = "#c7d2fe"
        green    = "#6ee7b7"
        amber    = "#fcd34d"
        surface  = "#1e293b"
    else:
        bg       = "#f8fafc"
        bg2      = "#ffffff"
        card_bg  = "rgba(255, 255, 255, 0.9)"
        card_bdr = "rgba(99, 102, 241, 0.12)"
        glass_bg = "rgba(255, 255, 255, 0.7)"
        text     = "#0f172a"
        sub      = "#475569"
        accent   = "#6366f1"
        accent2  = "#7c3aed"
        chip_bg  = "rgba(99, 102, 241, 0.08)"
        chip_bdr = "rgba(99, 102, 241, 0.18)"
        chip_clr = "#4f46e5"
        green    = "#059669"
        amber    = "#d97706"
        surface  = "#ffffff"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, sans-serif; }}
    .block-container {{ padding: 1rem 2rem 0 2rem !important; max-width: 1400px !important; }}
    .stApp {{ background: linear-gradient(145deg, {bg} 0%, {bg2} 100%) !important; }}

    /* ── Animated Header ── */
    .hero-header {{
        background: linear-gradient(135deg, {accent} 0%, {accent2} 50%, #ec4899 100%);
        background-size: 200% 200%;
        animation: gradientShift 6s ease infinite;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2rem; font-weight: 900; letter-spacing: -0.5px;
        margin: 0; padding: 0;
    }}
    @keyframes gradientShift {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}
    .hero-sub {{ color: {sub}; font-size: 0.92rem; margin-top: 2px; }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{
        background: linear-gradient(160deg, {bg} 0%, {bg2} 100%) !important;
        border-right: 1px solid {card_bdr};
    }}
    [data-testid="stSidebar"] * {{ color: {text} !important; }}
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stTextInput label {{ font-size: 0.82rem !important; opacity: 0.8; }}

    /* ── Job Detail Panel ── */
    .detail-panel {{
        background: {glass_bg};
        backdrop-filter: blur(14px);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        margin: 0.5rem 0 1rem;
    }}
    .detail-panel h4 {{
        color: {text}; font-size: 1rem; font-weight: 700;
        margin: 0 0 0.6rem; display: flex; align-items: center; gap: 8px;
    }}
    .detail-section {{
        margin-bottom: 0.8rem;
    }}
    .detail-section h5 {{
        color: {accent}; font-size: 0.82rem; font-weight: 600;
        margin: 0 0 4px; text-transform: uppercase; letter-spacing: 0.5px;
    }}
    .detail-section p, .detail-section li {{
        color: {sub}; font-size: 0.84rem; line-height: 1.6; margin: 2px 0;
    }}
    .detail-section ul {{ padding-left: 1.2rem; margin: 4px 0; }}
    .detail-tag {{
        display: inline-block; background: {chip_bg}; border: 1px solid {chip_bdr};
        color: {chip_clr}; font-size: 0.7rem; padding: 2px 10px;
        border-radius: 12px; margin: 2px 3px 2px 0;
    }}

    /* ── Glassmorphism Job Card ── */
    .jcard {{
        background: {card_bg};
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid {card_bdr};
        border-radius: 16px;
        padding: 1.3rem 1.5rem;
        margin-bottom: 0.85rem;
        transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
        position: relative;
        overflow: hidden;
    }}
    .jcard::before {{
        content: '';
        position: absolute; top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, {accent}, {accent2}, #ec4899);
        opacity: 0;
        transition: opacity 0.3s;
    }}
    .jcard:hover {{
        border-color: {accent};
        box-shadow: 0 8px 32px rgba(99,102,241,0.15);
        transform: translateY(-2px);
    }}
    .jcard:hover::before {{ opacity: 1; }}

    .jcard-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }}
    .jcard-logo {{
        width: 42px; height: 42px; border-radius: 10px;
        object-fit: contain; background: {surface};
        border: 1px solid {card_bdr}; padding: 4px;
    }}
    .jcard-logo-fallback {{
        width: 42px; height: 42px; border-radius: 10px;
        background: linear-gradient(135deg, {accent}, {accent2});
        display: flex; align-items: center; justify-content: center;
        font-size: 1.1rem; font-weight: 800; color: white;
    }}
    .jtitle {{ font-size: 1.05rem; font-weight: 700; color: {text}; margin: 0; line-height: 1.3; }}
    .jcompany {{ font-size: 0.82rem; color: {sub}; margin: 0; font-weight: 500; }}
    .jdesc {{ font-size: 0.84rem; color: {sub}; line-height: 1.6; margin: 8px 0; }}
    .jmeta {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}

    /* ── Badges ── */
    .badge {{
        display:inline-flex; align-items:center; gap:4px;
        font-size:0.7rem; font-weight:600;
        padding:3px 10px; border-radius:20px;
    }}
    .badge-loc   {{ background:rgba(59,130,246,0.1);  color:#60a5fa; border:1px solid rgba(59,130,246,0.2); }}
    .badge-type  {{ background:rgba(139,92,246,0.1);  color:#a78bfa; border:1px solid rgba(139,92,246,0.2); }}
    .badge-remote {{ background:rgba(52,211,153,0.1); color:{green};  border:1px solid rgba(52,211,153,0.2); }}
    .badge-salary {{ background:rgba(251,191,36,0.1); color:{amber};  border:1px solid rgba(251,191,36,0.2); }}
    .badge-time  {{ background:{chip_bg}; color:{chip_clr}; border:1px solid {chip_bdr}; }}
    .badge-score {{
        font-weight: 700; font-size: 0.72rem;
        padding: 3px 12px;
    }}
    .badge-score-high {{ background:rgba(52,211,153,0.15); color:{green}; border:1px solid rgba(52,211,153,0.3); }}
    .badge-score-mid  {{ background:rgba(251,191,36,0.12); color:{amber}; border:1px solid rgba(251,191,36,0.25); }}
    .badge-score-low  {{ background:rgba(239,68,68,0.1);   color:#f87171; border:1px solid rgba(239,68,68,0.2); }}

    /* ── Chat ── */
    .stChatMessage {{ border-radius:14px !important; background:{card_bg} !important;
                      border:1px solid {card_bdr} !important; backdrop-filter: blur(8px); }}
    [data-testid="stChatMessageContent"] p {{ font-size:0.92rem; line-height:1.7; color:{text}; }}

    /* ── Suggestion Chips ── */
    .sug-btn>button {{
        background: {chip_bg} !important; border: 1px solid {chip_bdr} !important;
        color: {chip_clr} !important; border-radius:20px !important;
        font-size:0.76rem !important; font-weight:500 !important;
        padding:4px 14px !important;
        transition: all 0.25s cubic-bezier(0.4,0,0.2,1) !important;
    }}
    .sug-btn>button:hover {{
        background: {accent} !important; color:white !important;
        border-color: {accent} !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(99,102,241,0.3);
    }}

    /* ── Profile Card ── */
    .profile-card {{
        background: linear-gradient(135deg, {accent}, {accent2});
        border-radius:14px; padding:1.1rem 1.3rem; color:white; margin-bottom:0.8rem;
        box-shadow: 0 4px 20px rgba(99,102,241,0.25);
    }}
    .profile-card h3 {{ margin:0; font-size:0.95rem; font-weight:700; }}
    .profile-card p  {{ margin:2px 0 0; font-size:0.78rem; opacity:0.85; }}

    /* ── Section Headers ── */
    .section-title {{
        font-size: 1.1rem; font-weight: 700; color: {text};
        display: flex; align-items: center; gap: 8px;
        margin-bottom: 0.6rem;
    }}

    /* ── Search Box ── */
    .stTextInput>div>div>input {{
        background: {surface} !important;
        border: 1px solid {card_bdr} !important;
        border-radius: 12px !important;
        color: {text} !important;
        font-size: 0.9rem !important;
    }}
    .stTextInput>div>div>input:focus {{
        border-color: {accent} !important;
        box-shadow: 0 0 0 2px rgba(99,102,241,0.15) !important;
    }}

    /* ── Misc ── */
    .stVerticalBlock {{ gap: 0 !important; }}
    .fit-reason {{ font-size: 0.82rem; color: {green}; font-style: italic; margin: 4px 0 0; }}
    .apply-link {{
        display: inline-flex; align-items: center; gap: 6px;
        background: linear-gradient(135deg, {accent}, {accent2});
        color: white !important; font-size: 0.8rem; font-weight: 600;
        padding: 6px 18px; border-radius: 10px;
        text-decoration: none; transition: all 0.2s;
        margin-top: 6px;
    }}
    .apply-link:hover {{
        box-shadow: 0 4px 16px rgba(99,102,241,0.35);
        transform: translateY(-1px);
    }}

    /* ── Skeleton Loader ── */
    @keyframes shimmer {{
        0% {{ background-position: -200% 0; }}
        100% {{ background-position: 200% 0; }}
    }}
    .skeleton {{
        background: linear-gradient(90deg, {card_bg} 25%, {card_bdr} 50%, {card_bg} 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 12px;
        height: 120px;
        margin-bottom: 0.8rem;
    }}
    </style>
    """, unsafe_allow_html=True)

inject_theme(st.session_state.dark_mode)


# ─────────────────────────────────────────────
#  DATABASE (profiles, applications, saved_jobs)
# ─────────────────────────────────────────────
class DB:
    def __init__(self):
        self.path = DB_PATH

    def _ex(self, sql, params=(), *, many=False, commit=False, one=False):
        try:
            con = sqlite3.connect(self.path)
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            if many:
                cur.executemany(sql, params)
            else:
                cur.execute(sql, params)
            if commit:
                con.commit()
                return cur.lastrowid
            if one:
                r = cur.fetchone()
                return dict(r) if r else None
            return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            return None
        finally:
            if 'con' in locals():
                con.close()

    # ── Profile ──
    def get_profile(self, email):
        return self._ex("SELECT * FROM profiles WHERE email=?", (email,), one=True)

    def save_profile(self, **kw):
        email = kw.get("email")
        if not email:
            return
        existing = self._ex("SELECT id FROM profiles WHERE email=?", (email,), one=True)
        if existing:
            sets = []
            vals = []
            for k, v in kw.items():
                if k != "email" and v is not None:
                    sets.append(f"{k}=?")
                    vals.append(v)
            if sets:
                vals.append(email)
                self._ex(f"UPDATE profiles SET {','.join(sets)}, updated_at=CURRENT_TIMESTAMP WHERE email=?",
                         tuple(vals), commit=True)
        else:
            cols = ["name","email","skills","tech_stack","experience_level",
                    "preferred_roles","preferred_locations","salary_min","salary_max",
                    "salary_currency","notice_period","resume_text"]
            vals = [kw.get(c, "" if c not in ("salary_min","salary_max") else 0) for c in cols]
            placeholders = ",".join(["?"] * len(cols))
            self._ex(f"INSERT INTO profiles ({','.join(cols)}) VALUES({placeholders})",
                     tuple(vals), commit=True)

    # ── Applications ──
    def apply(self, name, email, job):
        return self._ex(
            "INSERT INTO applications (name,email,status,job_api_id,job_title,job_company,job_location,apply_link) VALUES(?,?,?,?,?,?,?,?)",
            (name, email, "Applied", job.get("job_id",""), job.get("title",""),
             job.get("company",""), job.get("location",""), job.get("apply_link","")),
            commit=True
        )

    def my_apps(self, email):
        return self._ex("SELECT * FROM applications WHERE email=? ORDER BY id DESC", (email,)) or []

    def app_status(self, aid):
        return self._ex("SELECT * FROM applications WHERE id=?", (aid,), one=True)
        
    def update_app_status(self, aid, new_status):
        self._ex("UPDATE applications SET status=? WHERE id=?", (new_status, aid), commit=True)

    # ── Saved Jobs ──
    def save_job(self, email, job):
        try:
            self._ex(
                "INSERT OR IGNORE INTO saved_jobs (email,job_api_id,job_title,job_company,job_location,apply_link) VALUES(?,?,?,?,?,?)",
                (email, job.get("job_id",""), job.get("title",""),
                 job.get("company",""), job.get("location",""), job.get("apply_link","")),
                commit=True
            )
            return True
        except:
            return False

    def saved_jobs(self, email):
        return self._ex("SELECT * FROM saved_jobs WHERE email=? ORDER BY id DESC", (email,)) or []

    def remove_saved(self, email, job_api_id):
        self._ex("DELETE FROM saved_jobs WHERE email=? AND job_api_id=?", (email, job_api_id), commit=True)


# ─────────────────────────────────────────────
#  RESUME PARSER
# ─────────────────────────────────────────────
SKILL_VOCAB = {
    'python','javascript','react','sql','flask','django','aws','docker','git',
    'java','nodejs','typescript','c++','oop','machine learning','tensorflow',
    'pytorch','kubernetes','terraform','redis','postgresql','figma','excel',
    'tableau','selenium','html','css','node.js','rest api','microservices',
    'agile','scrum','seo','data visualization','deep learning','go','rust',
    'swift','kotlin','angular','vue','mongodb','graphql','fastapi','spark',
    'hadoop','kafka','airflow','jenkins','ci/cd','linux','bash','r',
    'power bi','salesforce','sap','nlp','generative ai','llm','opencv',
    'computer vision','pandas','numpy','spring boot','express',
}

def parse_resume(pdf_bytes):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = " ".join(p.extract_text() or "" for p in reader.pages)
        skills = [s for s in SKILL_VOCAB if s in text.lower()]
        email_m = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
        name_m  = re.search(r'^([A-Z][a-z]+ [A-Z][a-z]+)', text, re.MULTILINE)
        # Experience extraction
        exp_m  = re.search(r'(\d+)\+?\s*years?\s*(?:of\s+)?experience', text.lower())
        return {
            "text": text,
            "skills": skills,
            "email": email_m.group(0) if email_m else None,
            "name":  name_m.group(0)  if name_m  else "Candidate",
            "experience": exp_m.group(0) if exp_m else "",
        }
    except:
        return None


# ─────────────────────────────────────────────
#  INTENT CLASSIFIER
# ─────────────────────────────────────────────
class NLU:
    def __init__(self):
        try:
            with open(INT_PATH) as f:
                self.intents = json.load(f)['intents']
        except:
            self.intents = []

    def classify(self, text):
        t = text.lower()
        best_intent = "unknown"
        best_score  = 0

        for i in self.intents:
            for p in i['phrases']:
                phrase_words = set(re.findall(r'\w+', p.lower()))
                input_words  = set(re.findall(r'\w+', t))
                if not input_words:
                    continue
                overlap = len(phrase_words & input_words)
                score   = overlap / max(len(input_words), 1)
                if score > best_score:
                    best_score  = score
                    best_intent = i['intent']

        # Extra keyword fallbacks
        if re.search(r'\bapply\b', t) and re.search(r'\d+', t): return 'apply_job'
        if re.search(r'\bstatus\b', t):                          return 'check_status'
        if re.search(r'\bcover\s*letter\b', t):                  return 'generate_cover_letter'
        if re.search(r'\bresume\b.*\b(summary|tailor|help)\b', t): return 'generate_resume_summary'
        if re.search(r'\bcold\s*email\b', t):                    return 'generate_cold_email'
        if re.search(r'\bfind\b.*\bjob', t) or re.search(r'\bsearch\b.*\bjob', t): return 'search_jobs'
        if re.search(r'\binterview\b', t):                       return 'schedule_interview'

        if best_score < 0.2:
            return 'unknown'
        return best_intent


# ─────────────────────────────────────────────
#  INTERVIEW ENGINE
# ─────────────────────────────────────────────
INTERVIEW_QS = [
    "Tell me about yourself and your professional background.",
    "Tell me about your most impactful project. What technologies did you use, and what was the outcome?",
    "How do you handle tight deadlines or competing priorities in a fast-moving team?",
    "Describe a time you disagreed with a teammate. How did you resolve it?",
    "Can you explain a complex technical concept to a non-technical stakeholder?",
    "What motivates you to join our company specifically, and where do you see yourself in 3 years?",
    "What is your greatest professional achievement so far?",
    "Do you have any questions for us?"
]

def interview_feedback(answers):
    total_words = sum(len(a.split()) for a in answers)
    score = min(100, total_words // 3)
    if score >= 80:   grade, emoji = "Excellent", "🌟"
    elif score >= 55: grade, emoji = "Good",      "✅"
    elif score >= 30: grade, emoji = "Average",   "📊"
    else:             grade, emoji = "Needs Work", "📝"
    return f"""{emoji} **Interview Performance: {grade} ({score}/100)**

Here's a brief assessment of your responses:

• **Communication:** {"Clear and structured" if score > 60 else "Could be more detailed"}
• **Depth:** {"Strong technical depth demonstrated" if score > 70 else "Add more specifics and examples"}
• **Fit:** {"Great cultural fit signals" if score > 55 else "Align your answers to our mission more"}

Your interview notes have been saved. Our HR team will follow up within **3–5 business days**. 🚀"""


# ─────────────────────────────────────────────
#  BUILD USER PROFILE DICT (for API functions)
# ─────────────────────────────────────────────
def _build_profile_dict():
    """Build a profile dict from session state for API helper functions."""
    return {
        "name": st.session_state.uname,
        "email": st.session_state.email,
        "skills": ",".join(st.session_state.user_skills),
        "experience_level": st.session_state.get("exp_level", ""),
        "preferred_roles": st.session_state.get("pref_roles", ""),
        "preferred_locations": st.session_state.get("pref_locations", ""),
        "salary_min": st.session_state.get("salary_min", 0),
        "salary_max": st.session_state.get("salary_max", 0),
        "resume_text": st.session_state.get("resume_text", ""),
    }


# ─────────────────────────────────────────────
#  CHATBOT RESPONSE ENGINE
# ─────────────────────────────────────────────
def bot_reply(prompt: str) -> str:
    db  = st.session_state.db
    nlu = st.session_state.nlu
    intent = nlu.classify(prompt)

    # ── Interview mode ──
    if st.session_state.iv_mode:
        # Quit detection
        quit_words = {"quit", "exit", "stop", "cancel", "end", "leave", "skip"}
        if prompt.strip().lower() in quit_words:
            st.session_state.iv_mode = False
            answered = len(st.session_state.iv_answers)
            if answered > 0:
                feedback = interview_feedback(st.session_state.iv_answers)
                return f"🛑 **Interview ended early** (answered {answered}/{len(INTERVIEW_QS)} questions).\n\n{feedback}"
            return "🛑 **Interview cancelled.** No worries! Type *'start interview'* whenever you're ready to try again."

        st.session_state.iv_answers.append(prompt)
        st.session_state.iv_step += 1
        if st.session_state.iv_step < len(INTERVIEW_QS):
            q = INTERVIEW_QS[st.session_state.iv_step]
            return f"**Question {st.session_state.iv_step + 1} / {len(INTERVIEW_QS)}**\n\n{q}\n\n_Type **'quit'** to end the interview early._"
        else:
            st.session_state.iv_mode = False
            return interview_feedback(st.session_state.iv_answers)

    # ── Greet ──
    if intent == "greet":
        return ("Hello! 👋 I'm **TalentAI** — your AI-powered job assistant.\n\n"
                "Here's what I can do:\n\n"
                "• 🔍 **Search live jobs**: *'find remote python jobs'*\n"
                "• 🎯 **Match jobs to your resume**: upload your PDF in the sidebar\n"
                "• 📝 **Write cover letters**: *'cover letter for job #3'*\n"
                "• 📧 **Draft cold emails**: *'cold email for data analyst role'*\n"
                "• 📋 **Track applications**: *'status 2'*\n"
                "• 🎤 **Mock interview**: *'start interview'*\n\n"
                "How can I help you today?")

    # ── Farewell ──
    if intent == "farewell":
        return "Goodbye! 👋 Best of luck on your job search. Come back anytime!"

    # ── Search Jobs ──
    if intent in ("search_jobs", "job_openings"):
        # Use the prompt as the search query
        query = prompt.strip()
        # Clean up common prefixes
        for prefix in ["find me", "search for", "show me", "look for", "find", "search", "get me"]:
            if query.lower().startswith(prefix):
                query = query[len(prefix):].strip()

        if len(query) < 3:
            query = "software developer"

        result = search_jobs(query, num_pages=1)
        if result["error"]:
            return f"⚠️ {result['error']}"
        if not result["jobs"]:
            return f"No jobs found for *'{query}'*. Try different keywords — e.g., *'remote python developer'* or *'data analyst in New York'*."

        # Rank against profile
        profile = _build_profile_dict()
        jobs = rank_jobs_for_profile(result["jobs"], profile)
        st.session_state.last_search = jobs

        lines = [f"🔍 Found **{len(jobs)} jobs** for *'{query}'*:\n"]
        for i, j in enumerate(jobs[:6]):
            score   = j.get("match_score", 0)
            score_e = "🟢" if score >= 60 else ("🟡" if score >= 35 else "⚪")

            lines.append(f"**{i+1}. {j['title']}** at **{j['company']}**")
            lines.append(f"   📍 {j['location']} | {j['employment_type']} | {j['posted_at']}")
            if j.get("salary"):
                lines.append(f"   💰 {j['salary']}")
            lines.append(f"   {score_e} Match: {score}%")
            lines.append("")

        lines.append("_Type **'details 1'** to see full info, or **'apply 1'** to get the apply link._")
        lines.append("_You can also ask me to **write a cover letter** for any of these roles!_")
        return "\n".join(lines)

    # ── Suggest Jobs ──
    if intent == "suggest_jobs":
        if not st.session_state.user_skills:
            return "Upload your resume in the sidebar so I can match jobs to your skill set! 📄"

        skills_query = " ".join(st.session_state.user_skills[:5]) + " jobs"
        pref_loc = st.session_state.get("pref_locations", "")
        if pref_loc:
            skills_query += f" in {pref_loc}"

        result = search_jobs(skills_query, num_pages=1)
        if result["error"]:
            return f"⚠️ {result['error']}"
        if not result["jobs"]:
            return "Couldn't find matching jobs right now. Try updating your skills or broadening your preferences."

        profile = _build_profile_dict()
        jobs = rank_jobs_for_profile(result["jobs"], profile)
        st.session_state.last_search = jobs

        lines = ["🎯 **Top job matches for your profile:**\n"]
        for i, j in enumerate(jobs[:5]):
            score = j.get("match_score", 0)
            reasons = j.get("match_reasons", [])
            lines.append(f"**{i+1}. {j['title']}** at **{j['company']}** — _{score}% match_")
            if reasons:
                lines.append(f"   ✅ {reasons[0]}")
            lines.append("")

        lines.append("_Type **'details N'** or **'apply N'** to take action._")
        return "\n".join(lines)

    # ── Apply Job ──
    if intent == "apply_job":
        if not st.session_state.email:
            return "Please **upload your resume** in the sidebar first so I know who you are! 📄"

        ids = re.findall(r'\d+', prompt)
        if not ids:
            return "Which job would you like to apply for? Use the number from search results (e.g., *'apply 1'*)."

        idx = int(ids[0]) - 1
        jobs = st.session_state.get("last_search", [])
        if 0 <= idx < len(jobs):
            job = jobs[idx]
            app_id = db.apply(st.session_state.uname, st.session_state.email, job)
            return (f"🎉 **Application Submitted Automatically!**\n\n"
                    f"I have successfully applied to the **{job['title']}** role at **{job['company']}** on your behalf.\n\n"
                    f"**Reference ID:** #{app_id}\n\n"
                    f"You can check your status anytime by typing *'status {ids[0]}'*.")
        return f"Job #{ids[0]} not found in your last search. Run a search first!"

    # ── Check Status ──
    if intent == "check_status":
        ids = re.findall(r'\d+', prompt)
        if not ids:
            return "Please give me your Application ID. (e.g., *status 3*)"
        row = db.app_status(ids[0])
        if not row:
            return f"I couldn't find application **#{ids[0]}**. Double-check the ID."
        return (f"📋 **Application #{ids[0]}**\n\n"
                f"**Role:** {row.get('job_title','N/A')}\n"
                f"**Company:** {row.get('job_company','N/A')}\n"
                f"**Status:** {row['status']}\n"
                f"**Applied:** {row.get('applied_at','N/A')}")

    # ── Cover Letter ──
    if intent == "generate_cover_letter":
        if not st.session_state.email:
            return "Upload your resume first so I can tailor the cover letter to your background!"

        ids = re.findall(r'\d+', prompt)
        jobs = st.session_state.get("last_search", [])
        job = None
        if ids:
            idx = int(ids[0]) - 1
            if 0 <= idx < len(jobs):
                job = jobs[idx]

        if not job and jobs:
            job = jobs[0]

        if not job:
            return "Search for jobs first! Then tell me which one you'd like a cover letter for (e.g., *'cover letter for 2'*)."

        profile = _build_profile_dict()
        try:
            with st.spinner("✍️ Generating cover letter with AI..."):
                letter = generate_cover_letter(profile, job)
            return f"📝 **Cover Letter for {job['title']} at {job['company']}**\n\n---\n\n{letter}\n\n---\n\n_Copy and paste this into your application!_"
        except Exception:
            return f"📝 **Cover Letter for {job['title']} at {job['company']}**\n\n⚠️ Could not generate AI cover letter right now. Please try again in a moment."

    # ── Resume Summary ──
    if intent == "generate_resume_summary":
        if not st.session_state.email:
            return "Upload your resume first!"

        ids = re.findall(r'\d+', prompt)
        jobs = st.session_state.get("last_search", [])
        job = None
        if ids:
            idx = int(ids[0]) - 1
            if 0 <= idx < len(jobs):
                job = jobs[idx]
        if not job and jobs:
            job = jobs[0]
        if not job:
            return "Search for jobs first, then ask me to tailor your resume!"

        profile = _build_profile_dict()
        try:
            summary = generate_resume_summary(profile, job)
            return f"📄 **Tailored Resume Summary for {job['title']}**\n\n---\n\n{summary}\n\n---\n\n_Paste this at the top of your resume for maximum impact!_"
        except Exception:
            return f"📄 **Resume Summary for {job['title']}**\n\n⚠️ Could not generate AI summary right now. Please try again in a moment."

    # ── Cold Email ──
    if intent == "generate_cold_email":
        if not st.session_state.email:
            return "Upload your resume first!"

        ids = re.findall(r'\d+', prompt)
        jobs = st.session_state.get("last_search", [])
        job = None
        if ids:
            idx = int(ids[0]) - 1
            if 0 <= idx < len(jobs):
                job = jobs[idx]
        if not job and jobs:
            job = jobs[0]
        if not job:
            return "Search for jobs first, then I'll draft a cold email!"

        profile = _build_profile_dict()
        try:
            email_text = generate_cold_email(profile, job)
            return f"📧 **Cold Email for {job['title']} at {job['company']}**\n\n---\n\n{email_text}\n\n---\n\n_Ready to send!_"
        except Exception:
            return f"📧 **Cold Email for {job['title']}**\n\n⚠️ Could not generate AI email right now. Please try again in a moment."

    # ── Details ──
    if re.search(r'\bdetail', prompt.lower()):
        ids = re.findall(r'\d+', prompt)
        jobs = st.session_state.get("last_search", [])
        if ids:
            idx = int(ids[0]) - 1
            if 0 <= idx < len(jobs):
                j = jobs[idx]
                try:
                    reqs = extract_key_requirements(j)
                except Exception:
                    reqs = ["Review the full job description for details"]
                lines = [
                    f"### {j['title']} at {j['company']}\n",
                    f"📍 **Location:** {j['location']}",
                    f"💼 **Type:** {j['employment_type']}",
                    f"🕐 **Posted:** {j['posted_at']}",
                ]
                if j.get("salary"):
                    lines.append(f"💰 **Salary:** {j['salary']}")
                lines.append("\n**Key Requirements:**")
                for r in reqs:
                    lines.append(f"  • {r}")
                if j.get("match_reasons"):
                    lines.append(f"\n**Why it fits you:** {' '.join(j['match_reasons'][:2])}")
                if j.get("apply_link"):
                    lines.append(f"\n👉 **[Apply Now]({j['apply_link']})**")
                return "\n".join(lines)
        return "Use the number from your search results (e.g., *'details 1'*)."

    # ── Set Preferences ──
    if intent == "set_preferences":
        return ("To update your job preferences, use the **Profile Settings** in the sidebar.\n\n"
                "You can set:\n"
                "• Preferred locations\n• Experience level\n• Salary range\n• Target roles\n\n"
                "Or just tell me naturally, like: *'I'm looking for remote React roles around $120k'*")

    # ── Interview ──
    if intent == "schedule_interview":
        st.session_state.iv_mode = True
        st.session_state.iv_step = 0
        st.session_state.iv_answers = []
        return (f"🎤 **Starting Mock Interview – {len(INTERVIEW_QS)} Questions**\n\n"
                f"Take your time — there are no wrong answers.\n"
                f"_Type **'quit'** anytime to end the interview._\n\n"
                f"**Question 1 / {len(INTERVIEW_QS)}**\n\n{INTERVIEW_QS[0]}")

    # ── Leave Policy / Benefits — job-specific ──
    if intent == "leave_policy":
        ids = re.findall(r'\d+', prompt)
        jobs = st.session_state.get("last_search", [])
        if ids:
            idx = int(ids[0]) - 1
            if 0 <= idx < len(jobs):
                j = jobs[idx]
                benefits = j.get('benefits', [])
                lines = [f"📜 **Benefits & Leave Policy — {j['title']} at {j['company']}**\n"]
                if benefits:
                    for b in benefits:
                        lines.append(f"• {b}")
                else:
                    lines.append("ℹ️ This listing doesn't include specific leave/benefit details.")
                    lines.append("Each company sets its own policies — check the full listing or ask during your interview.")
                if j.get("apply_link"):
                    lines.append(f"\n👉 **[View Full Listing]({j['apply_link']})**")
                return "\n".join(lines)
        if jobs:
            return "Which job do you want benefits info for? Use the number from your search — e.g., *'benefits for 2'*."
        return "Search for jobs first, then ask about a specific job's benefits! Each company has its own policies."

    # ── Salary Info — job-specific ──
    if intent == "salary_info":
        ids = re.findall(r'\d+', prompt)
        jobs = st.session_state.get("last_search", [])
        if ids:
            idx = int(ids[0]) - 1
            if 0 <= idx < len(jobs):
                j = jobs[idx]
                lines = [f"💰 **Compensation — {j['title']} at {j['company']}**\n"]
                if j.get("salary"):
                    lines.append(f"**Listed Salary:** {j['salary']}")
                    if j.get("salary_period"):
                        lines.append(f"**Period:** {j['salary_period'].capitalize()}")
                    if j.get("salary_currency"):
                        lines.append(f"**Currency:** {j['salary_currency']}")
                else:
                    lines.append("ℹ️ Salary is not listed for this position.")
                    lines.append("💡 *Tip: Ask about compensation during the interview, or check Glassdoor/Levels.fyi for estimates.*")
                if j.get("apply_link"):
                    lines.append(f"\n👉 **[View Full Listing]({j['apply_link']})**")
                return "\n".join(lines)
        if jobs:
            return "Which job's salary do you want to check? Use the number from search — e.g., *'salary for 3'*."
        return "Search for jobs first, then I'll show you salary info for specific roles!"

    # ── Onboarding — redirect to job-specific info ──
    if intent == "onboarding_faq":
        jobs = st.session_state.get("last_search", [])
        if jobs:
            return ("🎓 **Onboarding varies by company.** Each employer has their own process.\n\n"
                    "📋 *Common things to prepare:*\n"
                    "• Government ID and educational certificates\n"
                    "• Bank details for payroll\n"
                    "• Signed offer letter\n\n"
                    "💡 For specifics, check the company's career page or ask during your interview.\n"
                    "Type **'details N'** to see a job's full description!")
        return ("🎓 Onboarding processes differ between companies.\n\n"
                "Search for jobs first, then type **'details N'** to see each company's specifics!")

    # ── Remote / WFH queries — help search ──
    if any(k in prompt.lower() for k in ["wfh", "work from home", "hybrid"]):
        return ("🏠 **Work arrangement varies by company and role.**\n\n"
                "I can help you find remote-friendly positions! Try:\n"
                "• *'find remote python jobs'*\n"
                "• *'find hybrid data analyst roles'*\n"
                "• Use the **🌐 Remote** filter on the job board")
    if any(k in prompt.lower() for k in ["hour", "timing", "office time"]):
        return ("⏰ **Work hours vary by company.**\n\n"
                "Most tech companies offer flexible hours. Check the specific job's description.\n"
                "Type **'details N'** to see a job's full info!")


    # ── Fallback ──
    return ("I didn't quite catch that — here are things you can try:\n\n"
            "• 🔍 *'find me remote python jobs'*\n"
            "• 🎯 *'match jobs to my resume'*\n"
            "• 📝 *'cover letter for job 2'*\n"
            "• 📧 *'cold email for 1'*\n"
            "• 📋 *'status 3'*\n"
            "• 🎤 *'start interview'*")


# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
if "boot" not in st.session_state:
    st.session_state.boot         = True
    st.session_state.email        = None
    st.session_state.uname        = "Candidate"
    st.session_state.user_skills  = []
    st.session_state.exp_level    = ""
    st.session_state.pref_roles   = ""
    st.session_state.pref_locations = ""
    st.session_state.salary_min   = 0
    st.session_state.salary_max   = 0
    st.session_state.resume_text  = ""
    st.session_state.db           = DB()
    st.session_state.nlu          = NLU()
    st.session_state.iv_mode      = False
    st.session_state.iv_step      = 0
    st.session_state.iv_answers   = []
    st.session_state.last_search  = []
    st.session_state.search_query = ""
    st.session_state.selected_job = None  # For inline job detail panel
    st.session_state.user_role    = "Candidate"
    st.session_state.app_mode     = "Job Board"
    st.session_state.messages     = [
        {"role": "assistant", "content": (
            "👋 **Welcome to TalentAI!** I'm your AI-powered job assistant.\n\n"
            "🔍 **Search live jobs** from thousands of companies worldwide\n"
            "📄 **Upload your resume** for personalized matching\n"
            "📝 **Generate cover letters** tailored to each role\n\n"
            "Start by uploading your resume in the sidebar, or type a query like *'find remote python developer jobs'*."
        )}
    ]


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚀 TalentAI")
    st.caption("AI-Powered Job Assistant")

    # ── Theme & Navigation ──
    theme_col, role_col = st.columns([1, 1])
    with theme_col:
        new_dark = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)
        if new_dark != st.session_state.dark_mode:
            st.session_state.dark_mode = new_dark
            st.rerun()
    with role_col:
        pass # Optional space

    st.markdown("### 🧭 Navigation")
    new_role = st.radio("Select Persona", ["Candidate", "HR / Recruiter"], 
                        index=0 if st.session_state.user_role == "Candidate" else 1,
                        horizontal=True, label_visibility="collapsed")
    if new_role != st.session_state.user_role:
        st.session_state.user_role = new_role
        st.session_state.app_mode = "Job Board" if new_role == "Candidate" else "ATS Dashboard"
        st.rerun()

    if st.session_state.user_role == "Candidate":
        tabs = ["Job Board", "My Applications", "Career Coach"]
    else:
        tabs = ["ATS Dashboard", "Job Draft Analyzer", "Culture Fit Generator"]

    new_mode = st.radio("Menu", tabs, 
                        index=tabs.index(st.session_state.app_mode) if st.session_state.app_mode in tabs else 0,
                        label_visibility="collapsed")
    if new_mode != st.session_state.app_mode:
        st.session_state.app_mode = new_mode
        st.rerun()

    st.divider()

    # ── Profile Block ──
    if st.session_state.email:
        st.markdown(f"""
        <div class="profile-card">
            <h3>👤 {st.session_state.uname}</h3>
            <p>{st.session_state.email}</p>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.user_skills:
            st.markdown("**🛠 Skills**")
            st.write(", ".join(s.capitalize() for s in st.session_state.user_skills[:15]))
            
        resume_text = f"# {st.session_state.uname}\n\n**Email:** {st.session_state.email}\n**Experience Level:** {st.session_state.exp_level.capitalize() if st.session_state.exp_level else 'Not Specified'}\n\n## Professional Summary\nPassionate professional eager to contribute to a dynamic team. Strong track record of continuous learning and adaptability.\n\n## Core Skills\n{', '.join(s.capitalize() for s in st.session_state.user_skills) if st.session_state.user_skills else 'General Professional Skills'}\n\n## Experience\n*Details extracted from original resume upload*\n"
        st.download_button("📥 Download ATS Resume", resume_text, f"{st.session_state.uname.replace(' ','_')}_Resume.txt", "text/plain", use_container_width=True)

        # ── Preferences Expander ──
        with st.expander("⚙️ Job Preferences", expanded=False):
            exp_opts = ["", "fresher", "junior", "mid", "senior", "lead"]
            exp = st.selectbox("Experience Level", exp_opts,
                               index=exp_opts.index(st.session_state.exp_level) if st.session_state.exp_level in exp_opts else 0)
            if exp != st.session_state.exp_level:
                st.session_state.exp_level = exp

            pref_loc = st.text_input("Preferred Locations", value=st.session_state.pref_locations,
                                      placeholder="e.g. Remote, India, New York")
            if pref_loc != st.session_state.pref_locations:
                st.session_state.pref_locations = pref_loc

            pref_roles = st.text_input("Preferred Roles", value=st.session_state.pref_roles,
                                        placeholder="e.g. Software Engineer, Data Analyst")
            if pref_roles != st.session_state.pref_roles:
                st.session_state.pref_roles = pref_roles

            sal_col1, sal_col2 = st.columns(2)
            sal_min = sal_col1.number_input("Min Salary", value=st.session_state.salary_min, step=10000, min_value=0)
            sal_max = sal_col2.number_input("Max Salary", value=st.session_state.salary_max, step=10000, min_value=0)
            if sal_min != st.session_state.salary_min:
                st.session_state.salary_min = sal_min
            if sal_max != st.session_state.salary_max:
                st.session_state.salary_max = sal_max

            if st.button("💾 Save Preferences", use_container_width=True):
                st.session_state.db.save_profile(
                    email=st.session_state.email,
                    name=st.session_state.uname,
                    skills=",".join(st.session_state.user_skills),
                    experience_level=exp,
                    preferred_locations=pref_loc,
                    preferred_roles=pref_roles,
                    salary_min=sal_min, salary_max=sal_max,
                )
                st.toast("✅ Preferences saved!", icon="💾")

        # ── My Applications ──
        apps = st.session_state.db.my_apps(st.session_state.email)
        if apps:
            st.divider()
            st.markdown("**📋 My Applications**")
            for a in apps[:5]:
                with st.expander(f"#{a['id']} – {a.get('job_title','N/A')}"):
                    st.write(f"🏢 {a.get('job_company','')}")
                    st.write(f"📍 {a.get('job_location','')}")
                    st.info(f"Status: **{a['status']}**")
                    if a.get('apply_link'):
                        st.markdown(f"[🔗 Apply Link]({a['apply_link']})")

        if st.button("🚪 Sign Out", use_container_width=True):
            for k in ["email","uname","user_skills","exp_level","pref_roles","pref_locations",
                       "salary_min","salary_max","resume_text","last_search"]:
                st.session_state[k] = None if k == "email" else ([] if k in ("user_skills","last_search") else ("" if isinstance(st.session_state.get(k), str) else 0))
            st.rerun()
    else:
        st.markdown("**📄 Upload Resume to Begin**")
        res = st.file_uploader("Drop your PDF here", type="pdf", label_visibility="collapsed")
        if res:
            data = parse_resume(res.read())
            if data:
                st.session_state.email       = data['email'] or "user@example.com"
                st.session_state.uname       = data['name']
                st.session_state.user_skills = data['skills']
                st.session_state.resume_text = data['text'][:3000]
                st.session_state.db.save_profile(
                    name=data['name'], email=st.session_state.email,
                    skills=",".join(data['skills']),
                    resume_text=data['text'][:3000],
                )
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": (
                        f"✅ **Resume analysed!**\n\n"
                        f"Hi **{data['name']}** 👋 I found **{len(data['skills'])} skills**: "
                        f"_{', '.join(data['skills'][:8])}_{'...' if len(data['skills'])>8 else ''}.\n\n"
                        f"Set your **job preferences** in the sidebar, then try:\n"
                        f"• *'find me remote python jobs'*\n"
                        f"• *'match jobs to my resume'*"
                    )
                })
                st.rerun()

    st.divider()
    st.markdown("**⚡ Quick Actions**")
    st.markdown('<div class="sug-btn">', unsafe_allow_html=True)
    qa = [
        ("🔍 Search Jobs",     "find software developer jobs"),
        ("🎯 Match Resume",    "match my resume"),
        ("📝 Cover Letter",    "cover letter for 1"),
        ("📧 Cold Email",      "cold email for 1"),
        ("🎤 Mock Interview",  "start interview"),
    ]
    for label, msg in qa:
        if st.button(label, use_container_width=True, key=f"qa_{label}"):
            st.session_state.messages.append({"role": "user", "content": label})
            try:
                reply = bot_reply(msg)
            except Exception:
                reply = "⚠️ Something went wrong. Please try again."
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  MAIN LAYOUT — Chat (left) | Jobs (right)
# ─────────────────────────────────────────────
# ── Animated Header ──
st.markdown("""
<div style="margin-bottom: 0.8rem;">
    <div class="hero-header">TalentAI</div>
    <div class="hero-sub">🔍 Search thousands of live jobs • 📝 AI-powered cover letters • 🎯 Smart matching</div>
</div>
""", unsafe_allow_html=True)

chat_col, jobs_col = st.columns([1, 1.35], gap="large")


# ═══════════════════════════════════════════════
#  LEFT — CHAT
# ═══════════════════════════════════════════════
with chat_col:
    st.markdown('<div class="section-title">💬 AI Assistant</div>', unsafe_allow_html=True)

    chat_box = st.container(height=520)
    for m in st.session_state.messages:
        chat_box.chat_message(m["role"]).write(m["content"])

    # Interview Progress Bar
    if st.session_state.iv_mode:
        pct = int(st.session_state.iv_step / len(INTERVIEW_QS) * 100)
        st.progress(pct, text=f"Interview – Question {st.session_state.iv_step+1}/{len(INTERVIEW_QS)}")

    # Suggestion chips
    if not st.session_state.iv_mode:
        sugg_cols = st.columns(3)
        chips = (
            [("🔍 Find Jobs", "find software developer jobs"),
             ("📝 Cover Letter", "cover letter for 1"),
             ("🎤 Interview", "start interview")]
            if st.session_state.email else
            [("🔍 Search Jobs", "find remote jobs"),
             ("🌐 Remote Jobs", "find remote developer jobs"),
             ("🎤 Interview", "start interview")]
        )
        for idx, (label, msg) in enumerate(chips):
            with sugg_cols[idx]:
                st.markdown('<div class="sug-btn">', unsafe_allow_html=True)
                if st.button(label, use_container_width=True, key=f"chip_{idx}_{label}"):
                    st.session_state.messages.append({"role": "user", "content": label})
                    try:
                        reply = bot_reply(msg)
                    except Exception:
                        reply = "⚠️ Something went wrong. Please try again."
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    if prompt := st.chat_input("Search jobs, ask for a cover letter, or type 'apply 1'..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        try:
            reply = bot_reply(prompt)
        except Exception:
            reply = "⚠️ Something went wrong processing your message. Please try again."
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()


# ═══════════════════════════════════════════════
#  RIGHT — LIVE JOB BOARD
# ═══════════════════════════════════════════════
with jobs_col:
    if st.session_state.app_mode == "Job Board":
        st.markdown('<div class="section-title">🌍 Live Job Board</div>', unsafe_allow_html=True)

        # ── Search Bar ──
        fc1, fc2, fc3 = st.columns([3, 1.5, 1])
        with fc1:
            search_q = st.text_input("🔍", placeholder="Search jobs... e.g. 'React developer in India'",
                                      label_visibility="collapsed", key="job_search_input")
        with fc2:
            emp_type = st.selectbox("Type", ["All", "Fulltime", "Parttime", "Intern", "Contractor"],
                                     label_visibility="collapsed")
        with fc3:
            remote_only = st.checkbox("🌐 Remote", value=False)

        # ── Trigger Search ──
        should_search = False
        if search_q and search_q != st.session_state.get("_last_board_query", ""):
            should_search = True
            st.session_state["_last_board_query"] = search_q

        if should_search or (not st.session_state.get("board_jobs") and not search_q):
            query = search_q if search_q else "software developer"
            emp_filter = "" if emp_type == "All" else emp_type.upper()

            with st.spinner("🔍 Fetching live jobs..."):
                result = search_jobs(query, num_pages=1, remote_only=remote_only,
                                      employment_type=emp_filter)

            if result["error"]:
                st.error(result["error"])
                st.session_state.board_jobs = []
            else:
                profile = _build_profile_dict()
                st.session_state.board_jobs = rank_jobs_for_profile(result["jobs"], profile)
                st.session_state.last_search = st.session_state.board_jobs

        jobs_list = st.session_state.get("board_jobs", [])

        st.caption(f"Showing **{len(jobs_list)}** live job{'s' if len(jobs_list) != 1 else ''}"
                   + (" — ranked by match score" if st.session_state.user_skills else ""))

        # ── Job Cards ──
        jscroll = st.container(height=530)
        with jscroll:
            # ── Inline Detail Panel (shown when a job is selected) ──
            sel = st.session_state.get("selected_job")
            if sel is not None and sel < len(jobs_list):
                sj = jobs_list[sel]
                try:
                    reqs = extract_key_requirements(sj)
                except Exception:
                    reqs = ["Review the full job description for details"]
                reasons = sj.get("match_reasons", [])

                # Build detail HTML
                detail_html = f'''<div class="detail-panel">
                    <h4>📋 {sj["title"]} — {sj["company"]}</h4>
                    <div class="detail-section">
                        <h5>📍 Location & Type</h5>
                        <p>{sj["location"]} • {sj["employment_type"]}
                        {"• 🌐 Remote" if sj.get("is_remote") else ""}
                        • Posted {sj["posted_at"]}</p>
                    </div>'''

                if sj.get("salary"):
                    detail_html += f'''<div class="detail-section">
                        <h5>💰 Compensation</h5>
                        <p>{sj["salary"]}</p>
                    </div>'''
                else:
                    detail_html += '''<div class="detail-section">
                        <h5>💰 Compensation</h5>
                        <p>Not listed — check the full posting or ask during interview</p>
                    </div>'''

                if sj.get("benefits"):
                    benefits_html = "".join(f"<li>{b}</li>" for b in sj["benefits"])
                    detail_html += f'''<div class="detail-section">
                        <h5>🎁 Benefits & Policies</h5>
                        <ul>{benefits_html}</ul>
                    </div>'''

                if reqs:
                    reqs_html = "".join(f"<li>{r}</li>" for r in reqs)
                    detail_html += f'''<div class="detail-section">
                        <h5>📌 Key Requirements</h5>
                        <ul>{reqs_html}</ul>
                    </div>'''

                if sj.get("tags"):
                    tags_html = "".join(f'<span class="detail-tag">{t}</span>' for t in sj["tags"][:10])
                    detail_html += f'''<div class="detail-section">
                        <h5>🏷️ Tags</h5>
                        <p>{tags_html}</p>
                    </div>'''

                if reasons and st.session_state.user_skills:
                    reasons_text = " • ".join(reasons[:3])
                    detail_html += f'''<div class="detail-section">
                        <h5>✨ Why It Fits You</h5>
                        <p>{reasons_text}</p>
                    </div>'''

                # Full description
                desc = sj.get("description", "")[:600]
                if desc:
                    import html as html_mod
                    desc_safe = html_mod.escape(desc)
                    detail_html += f'''<div class="detail-section">
                        <h5>📝 Description</h5>
                        <p>{desc_safe}…</p>
                    </div>'''

                detail_html += '</div>'
                st.markdown(detail_html, unsafe_allow_html=True)

                # Detail panel action buttons
                dp_cols = st.columns([1, 1, 1, 1])
                with dp_cols[0]:
                    if st.button("❌ Close", key="close_detail", use_container_width=True):
                        st.session_state.selected_job = None
                        st.rerun()
                with dp_cols[1]:
                    if sj.get("apply_link"):
                        st.markdown(
                            f'<a href="{sj["apply_link"]}" target="_blank" rel="noreferrer noopener" class="apply-link">'
                            f'🚀 Apply</a>',
                            unsafe_allow_html=True
                        )
                with dp_cols[2]:
                    if st.button("📝 Letter", key="dp_cl", use_container_width=True):
                        if st.session_state.email:
                            profile = _build_profile_dict()
                            try:
                                with st.spinner("Drafting letter..."):
                                    st.session_state[f"cl_{sj['job_id']}"] = generate_cover_letter(profile, sj)
                            except Exception:
                                st.error("⚠️ Could not generate right now. Try again in a moment.")
                        else:
                            st.error("Upload resume first!")
                            
                    if st.session_state.get(f"cl_{sj['job_id']}"):
                        st.text_area("Your Cover Letter", st.session_state[f"cl_{sj['job_id']}"], height=200, key=f"ta_{sj['job_id']}")
                        st.download_button("📥 Download .txt", st.session_state[f"cl_{sj['job_id']}"], f"Cover_Letter_{sj['company']}.txt", "text/plain", key=f"dl_{sj['job_id']}", use_container_width=True)
                with dp_cols[3]:
                    if st.button("💾 Save", key="dp_sv", use_container_width=True):
                        if st.session_state.email:
                            st.session_state.db.save_job(st.session_state.email, sj)
                            st.toast(f"💾 Saved: {sj['title']}", icon="⭐")
                        else:
                            st.error("Upload resume first!")
                st.divider()

            # ── Job List ──
            if not jobs_list:
                st.markdown('<div class="skeleton"></div>' * 3, unsafe_allow_html=True)
                st.info("Enter a search query above to find live jobs!")
            else:
                for idx, j in enumerate(jobs_list):
                    score = j.get("match_score", 0)

                    # Score badge class
                    if score >= 60:
                        score_cls = "badge-score-high"
                    elif score >= 35:
                        score_cls = "badge-score-mid"
                    else:
                        score_cls = "badge-score-low"

                    # Company logo
                    logo_url = j.get("company_logo")
                    if logo_url:
                        logo_html = f'<img src="{logo_url}" class="jcard-logo" alt="{j["company"]}">'
                    else:
                        initials = "".join(w[0] for w in j["company"].split()[:2]).upper()
                        logo_html = f'<div class="jcard-logo-fallback">{initials}</div>'

                    # Badges
                    badges = f'<span class="badge badge-loc">📍 {j["location"][:40]}</span>'
                    badges += f'<span class="badge badge-type">{j["employment_type"]}</span>'
                    if j.get("is_remote"):
                        badges += '<span class="badge badge-remote">🌐 Remote</span>'
                    if j.get("salary"):
                        badges += f'<span class="badge badge-salary">💰 {j["salary"]}</span>'
                    badges += f'<span class="badge badge-time">🕐 {j["posted_at"]}</span>'
                    if score > 0 and st.session_state.user_skills:
                        badges += f'<span class="badge badge-score {score_cls}">⭐ {score}% match</span>'

                    # Fit reason
                    fit_html = ""
                    reasons = j.get("match_reasons", [])
                    if reasons and st.session_state.user_skills:
                        fit_html = f'<div class="fit-reason">✨ {reasons[0]}</div>'

                    # Highlight selected job
                    is_selected = (sel is not None and sel == idx)
                    card_style = 'border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,0.25);' if is_selected else ''

                    st.markdown(f"""
                    <div class="jcard" style="{card_style}">
                        <div class="jcard-header">
                            {logo_html}
                            <div>
                                <div class="jtitle">{j['title']}</div>
                                <div class="jcompany">{j['company']}</div>
                            </div>
                        </div>
                        <div class="jmeta">{badges}</div>
                        <div class="jdesc">{j['description'][:180]}…</div>
                        {fit_html}
                    </div>
                    """, unsafe_allow_html=True)

                    # Action buttons — compact row
                    btn_cols = st.columns([1.2, 1, 1, 2])
                    with btn_cols[0]:
                        if st.button("📋 Details", key=f"det_{idx}", use_container_width=True):
                            st.session_state.selected_job = idx
                            st.rerun()

                    with btn_cols[1]:
                        if st.button("📝 Letter", key=f"cl_{idx}", use_container_width=True):
                            if st.session_state.email:
                                profile = _build_profile_dict()
                                try:
                                    letter = generate_cover_letter(profile, j)
                                    msg = f"📝 **Cover Letter for {j['title']} at {j['company']}**\n\n---\n\n{letter}\n\n---\n\n_Copy and use!_"
                                except Exception:
                                    msg = f"📝 **Cover Letter for {j['title']}**\n\n⚠️ Could not generate right now. Try again."
                                st.session_state.messages.append({"role": "assistant", "content": msg})
                                st.rerun()
                            else:
                                st.error("Upload resume first!")

                    with btn_cols[2]:
                        if st.button("💾 Save", key=f"sv_{idx}", use_container_width=True):
                            if st.session_state.email:
                                st.session_state.db.save_job(st.session_state.email, j)
                                st.toast(f"💾 Saved: {j['title']}", icon="⭐")
                            else:
                                st.error("Upload resume first!")

                    with btn_cols[3]:
                        if j.get("apply_link"):
                            st.markdown(
                                f'<a href="{j["apply_link"]}" target="_blank" rel="noreferrer noopener" class="apply-link">'
                                f'🚀 Apply on {j.get("publisher","Site")}</a>',
                                unsafe_allow_html=True
                            )

    elif st.session_state.app_mode == "My Applications":
        st.markdown('<div class="section-title">📂 My Applications Tracker</div>', unsafe_allow_html=True)
        if not st.session_state.email:
            st.warning("Please upload your resume in the sidebar to track applications.")
        else:
            apps = st.session_state.db.my_apps(st.session_state.email)
            if not apps:
                st.info("You haven't tracked any applications yet. Apply to jobs on the Job Board!")
            else:
                import pandas as pd
                import altair as alt
                df_apps = pd.DataFrame(apps)
                status_counts = df_apps['status'].value_counts().reset_index()
                status_counts.columns = ['Status', 'Count']
                chart = alt.Chart(status_counts).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                    x=alt.X('Status', sort=["Applied", "Interviewing", "Offer", "Rejected"]),
                    y='Count',
                    color=alt.Color('Status', scale=alt.Scale(domain=["Applied", "Interviewing", "Offer", "Rejected"], range=['#3b82f6', '#f59e0b', '#10b981', '#ef4444']), legend=None)
                ).properties(height=250, title="Pipeline Velocity")
                st.altair_chart(chart, use_container_width=True)
                st.divider()
                
                for idx, a in enumerate(apps):
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 2, 1])
                        with col1:
                            st.markdown(f"#### {a['job_title']}\n**{a['job_company']}** • 📍 {a['job_location']}")
                            st.caption(f"Applied on: {a['applied_at']}")
                        with col2:
                            statuses = ["Applied", "Interviewing", "Offer", "Rejected"]
                            current_stat = a["status"] if a["status"] in statuses else "Applied"
                            new_stat = st.selectbox("Status", statuses, index=statuses.index(current_stat), key=f"stat_{a['id']}", label_visibility="collapsed")
                            if new_stat != current_stat:
                                st.session_state.db.update_app_status(a["id"], new_stat)
                                st.rerun()
                        with col3:
                            if st.button("Follow-up Email", key=f"fu_{a['id']}", use_container_width=True):
                                with st.spinner("Drafting..."):
                                    profile = _build_profile_dict()
                                    job_mock = {"title": a["job_title"], "company": a["job_company"]}
                                    st.session_state[f"fu_email_{a['id']}"] = generate_follow_up_email(profile, job_mock)
                            
                            if st.session_state.get(f"fu_email_{a['id']}"):
                                st.text_area("Draft", st.session_state[f"fu_email_{a['id']}"], height=150, key=f"ta_fu_{a['id']}")
                                st.download_button("📥 Download", st.session_state[f"fu_email_{a['id']}"], f"Follow_Up_{a['job_company']}.txt", "text/plain", key=f"dl_fu_{a['id']}", use_container_width=True)

                            if st.button("💰 Negotiate", key=f"neg_{a['id']}", use_container_width=True):
                                with st.spinner("Drafting..."):
                                    profile = _build_profile_dict()
                                    job_mock = {"title": a["job_title"], "company": a["job_company"]}
                                    st.session_state[f"neg_script_{a['id']}"] = generate_salary_negotiation_script(profile, job_mock)
                                    
                            if st.session_state.get(f"neg_script_{a['id']}"):
                                st.text_area("Script", st.session_state[f"neg_script_{a['id']}"], height=150, key=f"ta_neg_{a['id']}")
                                st.download_button("📥 Download Script", st.session_state[f"neg_script_{a['id']}"], f"Negotiation_{a['job_company']}.txt", "text/plain", key=f"dl_neg_{a['id']}", use_container_width=True)

    elif st.session_state.app_mode == "Mock Interview":
        st.markdown('<div class="section-title">🎤 Mock Interview Simulator</div>', unsafe_allow_html=True)
        st.write("Simulate a behavioral interview for an upcoming role.")
        if not st.session_state.email:
            st.warning("Upload your resume to start an interview.")
        else:
            apps = st.session_state.db.my_apps(st.session_state.email)
            app_options = {f"{a['job_title']} at {a['job_company']}": a for a in apps} if apps else {}
            if not app_options:
                st.info("You need to save/apply for a job first to run a mock interview.")
            else:
                sel_app_label = st.selectbox("Select Job to Interview For:", list(app_options.keys()))
                sel_app = app_options[sel_app_label]
                
                if st.button("Start Interview Simulation", type="primary"):
                    st.session_state["mock_interview_active"] = True
                    st.session_state["mock_interview_history"] = [
                        {"role": "assistant", "content": f"Hi {st.session_state.uname}, I'm the hiring manager for the {sel_app['job_title']} role at {sel_app['job_company']}. Tell me a bit about your background and why you applied."}
                    ]
                    
                if st.session_state.get("mock_interview_active"):
                    for msg in st.session_state["mock_interview_history"]:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])
                            
                    if user_resp := st.chat_input("Your response..."):
                        st.session_state["mock_interview_history"].append({"role": "user", "content": user_resp})
                        st.chat_message("user").markdown(user_resp)
                        with st.spinner("Interviewer is typing..."):
                            from application_helper import _call_gemini
                            history_str = "\\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state["mock_interview_history"]])
                            prompt = f"You are a strict but fair hiring manager interviewing a candidate for a {sel_app['job_title']} role. Here is the conversation so far:\\n{history_str}\\n\\nAsk the next behavioral question. Keep it under 50 words. Do not break character."
                            try:
                                reply = _call_gemini(prompt) or "That's interesting. Tell me more."
                            except Exception:
                                reply = "That's interesting. Tell me more."
                            st.session_state["mock_interview_history"].append({"role": "assistant", "content": reply})
                            st.rerun()

    elif st.session_state.app_mode == "Career Coach":
        st.markdown('<div class="section-title">🧠 AI Career Coach</div>', unsafe_allow_html=True)
        if not st.session_state.email:
            st.warning("Upload your resume to get personalized coaching.")
        else:
            st.markdown("### Skill Gap Analysis")
            st.write("Compare your resume against any job posting to find missing skills and learning resources.")
            target_job = st.text_area("Paste Job Description here:", height=150)
            if st.button("🔍 Analyze Skill Gaps", type="primary"):
                if target_job:
                    with st.spinner("Analyzing..."):
                        profile = _build_profile_dict()
                        job_mock = {"description": target_job, "title": "Target Role", "company": "Company"}
                        analysis = generate_skill_gap_analysis(profile, job_mock)
                        st.session_state["last_analysis"] = analysis
                        
                else:
                    st.error("Please paste a job description first.")
                        
            if st.session_state.get("last_analysis"):
                st.markdown(f"**Analysis Result:**\n\n{st.session_state['last_analysis']}")
                st.download_button("📥 Download Analysis", st.session_state["last_analysis"], "Skill_Gap_Analysis.txt", "text/plain", key="dl_analysis")

    elif st.session_state.app_mode == "ATS Dashboard":
        st.markdown('<div class="section-title">🏢 ATS Dashboard (HR View)</div>', unsafe_allow_html=True)
        st.write("View all candidates who applied to roles.")
        apps = st.session_state.db._ex("SELECT * FROM applications ORDER BY id DESC")
        if not apps:
            st.info("No applications received yet.")
        else:
            import pandas as pd
            import altair as alt
            df = pd.DataFrame(apps)
            
            st.markdown("### Application Pipeline")
            col1, col2 = st.columns(2)
            with col1:
                status_counts = df['status'].value_counts().reset_index()
                status_counts.columns = ['Status', 'Count']
                chart1 = alt.Chart(status_counts).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta(field="Count", type="quantitative"),
                    color=alt.Color(field="Status", type="nominal"),
                    tooltip=['Status', 'Count']
                ).properties(height=300, title="Status Distribution")
                st.altair_chart(chart1, use_container_width=True)
            with col2:
                role_counts = df['job_title'].value_counts().head(5).reset_index()
                role_counts.columns = ['Job Role', 'Applications']
                chart2 = alt.Chart(role_counts).mark_bar(cornerRadiusEnd=5).encode(
                    y=alt.Y('Job Role', sort='-x', title=""),
                    x=alt.X('Applications', title=""),
                    color=alt.value('#6366f1'),
                    tooltip=['Job Role', 'Applications']
                ).properties(height=300, title="Top Roles by Volume")
                st.altair_chart(chart2, use_container_width=True)
                
            st.markdown("### Candidate Database")
            # Enhanced DataFrame with column configuration
            st.dataframe(
                df[["name", "email", "job_title", "job_company", "status", "applied_at"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "name": "Candidate",
                    "email": "Contact",
                    "job_title": "Role",
                    "job_company": "Company",
                    "status": st.column_config.SelectboxColumn("Status", options=["Applied", "Interviewing", "Offer", "Rejected"]),
                    "applied_at": st.column_config.DatetimeColumn("Date", format="D MMM YYYY")
                }
            )
            
            st.divider()
            st.markdown("### Onboarding Plan Generator")
            cand_name = st.selectbox("Select Candidate to Generate 30-60-90 Day Plan", df["name"].unique())
            cand_row = df[df["name"] == cand_name].iloc[0]
            if st.button("Generate Onboarding Plan", type="primary"):
                with st.spinner("Generating..."):
                    plan = generate_onboarding_plan(cand_row["name"], cand_row["job_title"])
                    st.session_state["last_onboarding_plan"] = plan
                    
            if st.session_state.get("last_onboarding_plan"):
                st.markdown(st.session_state["last_onboarding_plan"])
                st.download_button("📥 Download Plan", st.session_state["last_onboarding_plan"], f"Onboarding_{cand_name}.txt", "text/plain")

    elif st.session_state.app_mode == "Job Draft Analyzer":
        st.markdown('<div class="section-title">📝 D&I Job Draft Analyzer</div>', unsafe_allow_html=True)
        st.write("Paste your job draft to detect biased or exclusionary language.")
        draft = st.text_area("Job Draft:", height=200)
        if st.button("🕵️ Analyze Bias", type="primary"):
            if draft:
                with st.spinner("Analyzing language..."):
                    result = detect_job_bias(draft)
                    st.markdown(f"**Analysis Report:**\n\n{result}")
            else:
                st.error("Paste a draft first.")

    elif st.session_state.app_mode == "Culture Fit Generator":
        st.markdown('<div class="section-title">🤝 Culture Fit Questions</div>', unsafe_allow_html=True)
        st.write("Generate tailored behavioral questions for your upcoming interviews.")
        col1, col2 = st.columns(2)
        with col1:
            jtitle = st.text_input("Job Title")
        with col2:
            jcompany = st.text_input("Company Name")
            
        if st.button("Generate Questions", type="primary"):
            if jtitle and jcompany:
                with st.spinner("Generating..."):
                    q = generate_culture_fit_questions(jtitle, jcompany)
                    st.session_state["last_cf_q"] = q
                    
            if st.session_state.get("last_cf_q"):
                st.markdown(f"**Recommended Questions:**\n\n{st.session_state['last_cf_q']}")
                st.download_button("📥 Download Questions", st.session_state["last_cf_q"], f"Interview_Questions_{jcompany}.txt", "text/plain", key="dl_cf_q")
            else:
                st.error("Provide both title and company.")
