import os, json, sqlite3, re, io
import pandas as pd
import streamlit as st
import PyPDF2

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_DIR, 'hr_database.db')
INT_PATH  = os.path.join(BASE_DIR, 'hr_intents.json')

st.set_page_config(
    page_title="TalentAI – Recruitment Portal",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Init theme early so CSS is injected before everything else ──
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# ─────────────────────────────────────────────
#  PREMIUM CSS – Light & Dark Aware
# ─────────────────────────────────────────────
def inject_theme(dark: bool):
    if dark:
        bg, card_bg, card_border, text, sub = "#0e1117", "#1e2128", "#30363d", "#e6edf3", "#8b949e"
        chip_bg, chip_border, chip_color = "#21262d", "#30363d", "#c9d1d9"
    else:
        bg, card_bg, card_border, text, sub = "#f8fafc", "#ffffff", "#e2e8f0", "#0f172a", "#64748b"
        chip_bg, chip_border, chip_color = "#f8fafc", "#e2e8f0", "#334155"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .block-container {{ padding: 1.5rem 2rem 0 2rem !important; }}
    .stApp {{ background-color: {bg} !important; }}

    /* Sidebar always dark */
    [data-testid="stSidebar"] {{
        background: linear-gradient(160deg, #0f172a 0%, #1e293b 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.06);
    }}
    [data-testid="stSidebar"] * {{ color: #e2e8f0 !important; }}

    /* Job Cards */
    .jcard {{
        background: {card_bg};
        border: 1px solid {card_border};
        border-radius: 16px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 1rem;
        transition: box-shadow .2s, border-color .2s;
    }}
    .jcard:hover {{ box-shadow: 0 8px 30px rgba(0,0,0,0.12); border-color: #6366f1; }}
    .jtitle {{ font-size: 1.1rem; font-weight: 700; color: {text}; margin: 0.4rem 0 0.2rem; }}
    .jdesc  {{ font-size: 0.88rem; color: {sub}; line-height: 1.6; }}

    /* Badges */
    .badge {{ display:inline-block; font-size:0.72rem; font-weight:600;
               padding:3px 10px; border-radius:20px; margin-right:6px; margin-bottom:6px; }}
    .badge-dept  {{ background:#ede9fe; color:#5b21b6; }}
    .badge-loc   {{ background:#dbeafe; color:#1d4ed8; }}
    .badge-match {{ background:#d1fae5; color:#065f46; }}
    .badge-new   {{ background:#fef3c7; color:#92400e; }}

    /* Chat messages */
    .stChatMessage {{ border-radius:14px !important; background:{card_bg} !important;
                      border:1px solid {card_border} !important; }}
    [data-testid="stChatMessageContent"] p {{ font-size:0.95rem; line-height:1.7; color:{text}; }}

    /* Suggestion chips */
    .sug-btn>button {{
        background: {chip_bg} !important; border: 1px solid {chip_border} !important;
        color: {chip_color} !important; border-radius:20px !important;
        font-size:0.78rem !important; font-weight:500 !important;
        padding:4px 14px !important; transition:all .2s !important;
    }}
    .sug-btn>button:hover {{
        background:#6366f1 !important; color:white !important; border-color:#6366f1 !important;
    }}

    /* Profile card */
    .profile-card {{
        background: linear-gradient(135deg,#6366f1,#8b5cf6);
        border-radius:14px; padding:1.2rem 1.4rem; color:white; margin-bottom:1rem;
    }}
    .profile-card h3 {{ margin:0; font-size:1rem; font-weight:700; }}
    .profile-card p  {{ margin:0; font-size:0.82rem; opacity:0.85; }}
    .stVerticalBlock {{ gap:0 !important; }}
    </style>
    """, unsafe_allow_html=True)

inject_theme(st.session_state.dark_mode)


# ─────────────────────────────────────────────
#  DATABASE
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

    def jobs(self):          return self._ex("SELECT * FROM jobs") or []
    def job(self, jid):      return self._ex("SELECT * FROM jobs WHERE id=?", (jid,), one=True)
    def faqs(self):          return self._ex("SELECT * FROM faqs") or []
    def app_status(self, aid): return self._ex("SELECT a.*,j.title FROM applications a JOIN jobs j ON a.position_id=j.id WHERE a.id=?", (aid,), one=True)
    def my_apps(self, email): return self._ex("SELECT a.*,j.title,j.location FROM applications a JOIN jobs j ON a.position_id=j.id WHERE a.email=?", (email,)) or []

    def apply(self, name, email, jid):
        return self._ex(
            "INSERT INTO applications (name,email,status,position_id) VALUES(?,?,?,?)",
            (name, email, "Under Review", jid), commit=True
        )

    def save_profile(self, name, email, skills, resume_text):
        existing = self._ex("SELECT id FROM profiles WHERE email=?", (email,), one=True)
        if existing:
            self._ex("UPDATE profiles SET name=?,skills=?,resume_text=? WHERE email=?",
                     (name, skills, resume_text, email), commit=True)
        else:
            self._ex("INSERT INTO profiles (name,email,skills,resume_text) VALUES(?,?,?,?)",
                     (name, email, skills, resume_text), commit=True)


# ─────────────────────────────────────────────
#  RESUME PARSER
# ─────────────────────────────────────────────
SKILL_VOCAB = {
    'python','javascript','react','sql','flask','django','aws','docker','git',
    'java','nodejs','typescript','c++','oop','machine learning','tensorflow',
    'pytorch','kubernetes','terraform','redis','postgresql','figma','excel',
    'tableau','selenium','html','css','node.js','rest api','microservices',
    'agile','scrum','seo','data visualization','deep learning'
}

def parse_resume(pdf_bytes):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = " ".join(p.extract_text() or "" for p in reader.pages)
        skills = [s for s in SKILL_VOCAB if s in text.lower()]
        email_m = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
        name_m  = re.search(r'^([A-Z][a-z]+ [A-Z][a-z]+)', text, re.MULTILINE)
        return {
            "text": text,
            "skills": skills,
            "email": email_m.group(0) if email_m else None,
            "name":  name_m.group(0)  if name_m  else "Candidate",
        }
    except:
        return None

def match_score(job_skills_str, user_skills):
    job_skills = {s.strip().lower() for s in job_skills_str.split(',')}
    matched    = job_skills & set(user_skills)
    return int(len(matched) / max(len(job_skills), 1) * 100), list(matched)


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
        for i in self.intents:
            for p in i['phrases']:
                if p.lower() in t:
                    return i['intent']
        # Extra keyword fallbacks
        if re.search(r'\bapply\b', t) and re.search(r'\d+', t): return 'apply_job'
        if re.search(r'\bstatus\b', t):                          return 'check_status'
        if re.search(r'\binterview\b', t):                       return 'schedule_interview'
        return 'unknown'


# ─────────────────────────────────────────────
#  INTERVIEW ENGINE
# ─────────────────────────────────────────────
INTERVIEW_QS = [
    "Tell me about your most impactful project. What technologies did you use, and what was the outcome?",
    "How do you handle tight deadlines or competing priorities in a fast-moving team?",
    "Describe a time you disagreed with a teammate. How did you resolve it?",
    "What motivates you to join our company specifically, and where do you see yourself in 3 years?",
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

Your interview notes have been saved to your profile. Our HR team will follow up within **3–5 business days**. 🚀"""


# ─────────────────────────────────────────────
#  CHATBOT RESPONSE ENGINE
# ─────────────────────────────────────────────
def bot_reply(prompt: str) -> str:
    db  = st.session_state.db
    nlu = st.session_state.nlu
    intent = nlu.classify(prompt)

    # ── Interview mode ──────────────────────
    if st.session_state.iv_mode:
        step = st.session_state.iv_step
        st.session_state.iv_answers.append(prompt)
        st.session_state.iv_step += 1
        if st.session_state.iv_step < len(INTERVIEW_QS):
            q = INTERVIEW_QS[st.session_state.iv_step]
            return f"**Question {st.session_state.iv_step + 1} / {len(INTERVIEW_QS)}**\n\n{q}"
        else:
            st.session_state.iv_mode = False
            return interview_feedback(st.session_state.iv_answers)

    # ── Greet ────────────────────────────────
    if intent == "greet":
        return ("Hello! 👋 I'm **TalentAI** – your smart HR partner. Here's what I can do:\n\n"
                "• 🏢 Show you open jobs\n• 📄 Match jobs to your resume\n"
                "• 🚀 Apply directly: *type 'apply 3'*\n• 📋 Track status: *type 'status 2'*\n"
                "• 📜 Answer HR policies\n• 🎤 Run a mock interview\n\nHow can I help?")

    # ── Farewell ─────────────────────────────
    if intent == "farewell":
        return "Goodbye! 👋 Best of luck on your journey. We hope to see you at TalentAI soon!"

    # ── Job Openings ─────────────────────────
    if intent == "job_openings":
        jobs = db.jobs()
        if not jobs: return "No openings right now. Please check back soon!"
        lines = ["Here are our **current open positions**:\n"]
        for j in jobs[:8]:
            lines.append(f"**#{j['id']} – {j['title']}** | {j['department']} | 📍 {j['location']}")
        lines.append("\n_Type 'apply [ID]' to apply, or go to the **Job Board** tab._")
        return "\n".join(lines)

    # ── Suggest Jobs ─────────────────────────
    if intent == "suggest_jobs":
        if not st.session_state.user_skills:
            return "Upload your resume in the sidebar so I can match jobs to your skill set! 📄"
        jobs = db.jobs()
        scored = []
        for j in jobs:
            pct, matched = match_score(j['skills'], st.session_state.user_skills)
            scored.append((pct, matched, j))
        scored.sort(key=lambda x: x[0], reverse=True)
        lines = ["🎯 **Top job matches for your profile:**\n"]
        for pct, matched, j in scored[:5]:
            if pct > 0:
                lines.append(f"**#{j['id']} – {j['title']}** – _{pct}% match_ ✅ {', '.join(matched[:3])}")
        if len(lines) == 1: return "No strong matches found. Try uploading a more detailed resume."
        return "\n".join(lines)

    # ── Direct Apply ─────────────────────────
    if intent == "apply_job":
        if not st.session_state.email:
            return "Please **upload your resume** in the sidebar first so I know who you are! 📄"
        ids = re.findall(r'\d+', prompt)
        if not ids: return "Which job ID would you like to apply for? (e.g., *apply 3*)"
        job = db.job(ids[0])
        if not job: return f"No job found with ID **#{ids[0]}**. Check the Job Board tab for valid IDs."
        app_id = db.apply(st.session_state.uname, st.session_state.email, ids[0])
        st.session_state.last_applied = {"app_id": app_id, "title": job['title']}
        return (f"🎉 **Application Submitted!**\n\n"
                f"**Role:** {job['title']}\n**Reference ID:** #{app_id}\n**Status:** Under Review\n\n"
                f"Would you like to do a quick **mock interview** to boost your chances? Type *start interview*.")

    # ── Check Status ─────────────────────────
    if intent == "check_status":
        ids = re.findall(r'\d+', prompt)
        if not ids: return "Please give me your Application ID. (e.g., *status 3*)"
        row = db.app_status(ids[0])
        if not row: return f"I couldn't find application **#{ids[0]}**. Double-check the ID."
        STATUS_ICON = {"Under Review": "🔍", "Interview Scheduled": "📅", "Offer Extended": "🎁",
                       "Rejected": "❌", "Pending Review": "⏳", "Applied": "✅"}
        icon = STATUS_ICON.get(row['status'], "📋")
        return (f"{icon} **Application #{ids[0]} – {row['title']}**\n\n"
                f"**Current Status:** {row['status']}\n\nOur team is actively processing your application.")

    # ── Leave Policy ─────────────────────────
    if intent == "leave_policy":
        return ("📜 **Leave Policy Summary**\n\n"
                "• 🏖️ **Annual Leave:** 25 paid days per year\n"
                "• 🤒 **Sick Leave:** 12 days (no carry-over)\n"
                "• 🐣 **Maternity Leave:** 26 weeks fully paid\n"
                "• 👨‍🍼 **Paternity Leave:** 4 weeks fully paid\n\n"
                "_Applications must be submitted at least 2 weeks in advance via the HR portal._")

    # ── Salary ───────────────────────────────
    if intent == "salary_info":
        return ("💰 **Salary & Compensation**\n\n"
                "• Salaries are credited on the **last working day** of each month\n"
                "• Annual appraisals happen every **Q1** (January–March)\n"
                "• Bonuses are linked to performance reviews\n"
                "• Payslips are available on the **Employee Self-Service portal**")

    # ── Onboarding ───────────────────────────
    if intent == "onboarding_faq":
        return ("🎓 **Onboarding FAQ**\n\n"
                "• **Documents needed:** ID proof, educational certificates, previous offer letters\n"
                "• **Dress Code:** Smart casual\n"
                "• **Day 1:** Orientation at 9:00 AM – meet your buddy and manager\n"
                "• **Laptop:** Pre-configured and ready on arrival\n"
                "• **Access:** IT will set up all accounts within 24 hours")

    # ── Resignation ──────────────────────────
    if intent == "resignation_process":
        return ("📋 **Resignation Process**\n\n"
                "• Standard notice period is **30 days**\n"
                "• Submit your resignation letter to your manager + HR via email\n"
                "• Exit interview is mandatory\n"
                "• Your clearance certificate and relieving letter are issued within **7 working days** after the last day")

    # ── Interview ────────────────────────────
    if intent == "schedule_interview":
        st.session_state.iv_mode = True
        st.session_state.iv_step = 0
        st.session_state.iv_answers = []
        return (f"🎤 **Starting Mock Interview – {len(INTERVIEW_QS)} Questions**\n\n"
                f"Take your time — there are no wrong answers. Here we go!\n\n"
                f"**Question 1 / {len(INTERVIEW_QS)}**\n\n{INTERVIEW_QS[0]}")

    # ── WFH / Hours ──────────────────────────
    if any(k in prompt.lower() for k in ["wfh", "remote", "work from home", "hybrid"]):
        return "🏠 We follow a **hybrid model**: 3 days onsite + 2 days WFH per week. Fully remote roles are marked on the job board."
    if any(k in prompt.lower() for k in ["hour", "timing", "office time"]):
        return "⏰ Core hours are **9:00 AM – 6:00 PM**, Mon–Fri. Flexible start (8–10 AM) is allowed with manager approval."

    # ── Health / Benefits ────────────────────
    if any(k in prompt.lower() for k in ["insurance", "health", "benefit", "medical"]):
        return ("🏥 **Benefits Package:**\n\n"
                "• Comprehensive health insurance (you + family)\n"
                "• Dental & vision coverage\n"
                "• ₹10,000 monthly wellness allowance\n"
                "• Life & accident insurance\n"
                "• Employee Stock Options (ESOP) for senior roles")

    # ── Fallback ─────────────────────────────
    return ("I didn't quite catch that — here are some things you can try:\n\n"
            "• 🏢 *show me jobs*\n• 🎯 *match jobs to my resume*\n"
            "• 🚀 *apply 3* (replace 3 with a job ID)\n• 📋 *status 2*\n"
            "• 📜 *leave policy* / *salary info*\n• 🎤 *start interview*")


# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
if "boot" not in st.session_state:
    st.session_state.boot         = True
    st.session_state.email        = None
    st.session_state.uname        = "Candidate"
    st.session_state.user_skills  = []
    st.session_state.db           = DB()
    st.session_state.nlu          = NLU()
    st.session_state.iv_mode      = False
    st.session_state.iv_step      = 0
    st.session_state.iv_answers   = []
    st.session_state.last_applied = None
    st.session_state.messages     = [
        {"role": "assistant", "content": (
            "👋 **Welcome to TalentAI!** I'm your smart HR partner.\n\n"
            "Upload your resume in the sidebar to unlock **personalised job matching**, "
            "or click a quick action below to get started."
        )}
    ]


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💼 TalentAI")
    st.caption("Your intelligent recruitment partner")

    # ── Dark / Light Mode Toggle ──
    new_dark = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)
    if new_dark != st.session_state.dark_mode:
        st.session_state.dark_mode = new_dark
        inject_theme(new_dark)
        st.rerun()

    st.divider()

    # ── Profile Block ──
    if st.session_state.email:
        pct_filled = min(100, 40 + len(st.session_state.user_skills) * 5)
        st.markdown(f"""
        <div class="profile-card">
            <h3>👤 {st.session_state.uname}</h3>
            <p>{st.session_state.email}</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(pct_filled, text=f"Profile {pct_filled}% complete")
        if st.session_state.user_skills:
            st.markdown("**🛠 Detected Skills**")
            st.write(", ".join(s.capitalize() for s in st.session_state.user_skills[:12]))

        apps = st.session_state.db.my_apps(st.session_state.email)
        if apps:
            st.divider()
            st.markdown("**📋 My Applications**")
            for a in apps:
                with st.expander(f"#{a['id']} – {a['title']}"):
                    st.write(f"📍 {a['location']}")
                    st.info(f"Status: **{a['status']}**")
        if st.button("Sign Out", use_container_width=True):
            for k in ["email","uname","user_skills"]:
                st.session_state[k] = None if k=="email" else []
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
                st.session_state.db.save_profile(
                    data['name'], st.session_state.email,
                    ",".join(data['skills']), data['text'][:3000]
                )
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": (
                        f"✅ **Resume analysed!**\n\n"
                        f"Hi **{data['name']}** 👋 I found **{len(data['skills'])} skills** in your resume: "
                        f"_{', '.join(data['skills'][:6])}_{'...' if len(data['skills'])>6 else ''}.\n\n"
                        f"Head to the **Job Board** to see your personalised matches, or type *'match my resume'* here!"
                    )
                })
                st.rerun()

    st.divider()
    st.markdown("**⚡ Quick Actions**")
    st.markdown('<div class="sug-btn">', unsafe_allow_html=True)
    qa = [
        ("🏢 Open Roles",    "show me jobs"),
        ("🎯 Match Resume",  "match my resume"),
        ("📜 Leave Policy",  "leave policy"),
        ("💰 Salary Info",   "salary info"),
        ("🎤 Mock Interview","start interview"),
        ("🏠 WFH Policy",    "work from home policy"),
    ]
    for label, msg in qa:
        if st.button(label, use_container_width=True, key=f"qa_{label}"):
            st.session_state.messages.append({"role": "user",      "content": label})
            st.session_state.messages.append({"role": "assistant", "content": bot_reply(msg)})
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  MAIN LAYOUT  –  Chat (left) | Jobs (right)
# ─────────────────────────────────────────────
chat_col, jobs_col = st.columns([1, 1.3], gap="large")

# ══════════════════════════════════════════════
#  LEFT  —  CHAT
# ══════════════════════════════════════════════
with chat_col:
    st.markdown("### 💬 HR AI Assistant")

    chat_box = st.container(height=520)
    for m in st.session_state.messages:
        chat_box.chat_message(m["role"]).write(m["content"])

    # Interview Progress Bar
    if st.session_state.iv_mode:
        pct = int(st.session_state.iv_step / len(INTERVIEW_QS) * 100)
        st.progress(pct, text=f"Interview – Question {st.session_state.iv_step+1}/{len(INTERVIEW_QS)}")

    # Inline suggestion chips (context‑aware)
    if not st.session_state.iv_mode:
        sugg_cols = st.columns(3)
        chips = (
            [("📋 My Status",  "status"), ("🎯 Match Me",   "match my resume"), ("🎤 Interview", "start interview")]
            if st.session_state.email else
            [("🏢 View Jobs", "show me jobs"), ("📜 Leave Policy", "leave policy"), ("💰 Salary", "salary info")]
        )
        for idx, (label, msg) in enumerate(chips):
            with sugg_cols[idx]:
                st.markdown('<div class="sug-btn">', unsafe_allow_html=True)
                if st.button(label, use_container_width=True, key=f"chip_{idx}_{label}"):
                    st.session_state.messages.append({"role": "user",      "content": label})
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply(msg)})
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    if prompt := st.chat_input("Ask me anything… or type 'apply 3'"):
        st.session_state.last_applied = None
        st.session_state.messages.append({"role": "user", "content": prompt})
        reply = bot_reply(prompt)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        if st.session_state.last_applied:
            st.balloons()
        st.rerun()


# ══════════════════════════════════════════════
#  RIGHT  —  JOB BOARD
# ══════════════════════════════════════════════
with jobs_col:
    st.markdown("### 🚀 Open Opportunities")

    jobs_raw = st.session_state.db.jobs()

    # Score & sort
    jobs_scored = []
    for j in jobs_raw:
        pct, matched = match_score(j['skills'], st.session_state.user_skills)
        jobs_scored.append({**j, "pct": pct, "matched": matched})
    jobs_scored.sort(key=lambda x: x["pct"], reverse=True)

    # Filters
    fc1, fc2 = st.columns([2, 1])
    search = fc1.text_input("🔍 Search roles...", placeholder="e.g. Engineer, Remote, Python")
    depts  = sorted({j['department'] for j in jobs_raw})
    dept   = fc2.selectbox("Department", ["All"] + depts, label_visibility="collapsed")

    filtered = [
        j for j in jobs_scored
        if (not search or any(search.lower() in j[f].lower() for f in ['title','department','location','skills']))
        and (dept == "All" or j['department'] == dept)
    ]

    st.caption(f"Showing **{len(filtered)}** role{'s' if len(filtered)!=1 else ''}"
               + (f" – sorted by match score" if st.session_state.user_skills else ""))

    jscroll = st.container(height=560)          # scrollable job list
    with jscroll:
        for j in filtered:
            pct     = j['pct']
            matched = j['matched']

            # Build badge HTML
            badges  = f'<span class="badge badge-dept">{j["department"]}</span>'
            badges += f'<span class="badge badge-loc">📍 {j["location"]}</span>'
            if pct > 0:
                badges += f'<span class="badge badge-match">⭐ {pct}% match</span>'
            # NEW badge for high‑match unopened roles
            if pct >= 70:
                badges += '<span class="badge badge-new">🔥 Top Pick</span>'

            st.markdown(f"""
            <div class="jcard">
                {badges}
                <div class="jtitle">#{j['id']} — {j['title']}</div>
                <div class="jdesc">{j['description'][:160]}…</div>
            </div>
            """, unsafe_allow_html=True)

            exp_col, btn_col = st.columns([4, 1])
            with exp_col:
                with st.expander("Details & Skills"):
                    st.markdown(f"**Full Description**\n\n{j['description']}")
                    st.markdown("**Required Skills**")
                    skill_list = [s.strip() for s in j['skills'].split(',') if s.strip()]
                    if skill_list:
                        ncols = min(3, len(skill_list))
                        cols  = st.columns(ncols)
                        for ci, sk in enumerate(skill_list[:9]):
                            hi = sk.lower() in matched
                            cols[ci % ncols].markdown(f"{'✅' if hi else '⬜'} `{sk}`")
                    if matched:
                        st.success(f"Your matching skills: **{', '.join(matched[:5])}**")

            with btn_col:
                if st.button("Apply", key=f"jb_{j['id']}", use_container_width=True):
                    if not st.session_state.email:
                        st.error("Upload resume first!")
                    else:
                        app_id = st.session_state.db.apply(
                            st.session_state.uname, st.session_state.email, j['id']
                        )
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": (
                                f"🎉 **Applied for {j['title']}!**\n\n"
                                f"**Reference ID:** #{app_id}  |  **Status:** Under Review\n\n"
                                f"Type *'start interview'* to do a mock screening and stand out! 🎤"
                            )
                        })
                        st.toast(f"✅ Applied! Ref #{app_id}", icon="🚀")
                        st.balloons()
                        st.rerun()
