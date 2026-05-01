"""
Application Helper — Generates cover letters, resume summaries, and cold emails.
Uses Google Gemini API for high-quality generation, with template fallback.
"""

import os
import re
import json
import time
import requests

# ─────────────────────────────────────────────
#  GEMINI CONFIG
# ─────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.0-flash"
GEMINI_URL     = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def _call_gemini(prompt: str) -> str | None:
    """Call Gemini API with retry on rate limits. Returns None on ANY failure — never raises."""
    if not GEMINI_API_KEY:
        return None

    for attempt in range(3):
        try:
            resp = requests.post(
                GEMINI_URL,
                params={"key": GEMINI_API_KEY},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 1200,
                    }
                },
                timeout=20,
            )

            # Rate limit — retry
            if resp.status_code == 429:
                wait = (2 ** attempt) + 1
                time.sleep(wait)
                continue

            # Other HTTP errors — bail
            if resp.status_code >= 400:
                return None

            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
            return None

        except requests.exceptions.Timeout:
            continue  # retry on timeout
        except Exception:
            return None  # any other error — give up silently

    return None


# ─────────────────────────────────────────────
#  PROFILE → CONTEXT STRING
# ─────────────────────────────────────────────
def _profile_context(profile: dict) -> str:
    """Build a human-readable summary of the user profile for prompts."""
    lines = []
    if profile.get("name"):
        lines.append(f"Name: {profile['name']}")
    if profile.get("skills"):
        lines.append(f"Technical Skills: {profile['skills']}")
    if profile.get("experience_level"):
        lines.append(f"Experience Level: {profile['experience_level']}")
    if profile.get("preferred_roles"):
        lines.append(f"Preferred Roles: {profile['preferred_roles']}")
    if profile.get("preferred_locations"):
        lines.append(f"Preferred Locations: {profile['preferred_locations']}")
    if profile.get("resume_text"):
        lines.append(f"Resume Excerpt:\n{profile['resume_text'][:1500]}")
    return "\n".join(lines) if lines else "No profile information available."


def _job_context(job: dict) -> str:
    """Build a concise job summary for prompts."""
    lines = [
        f"Job Title: {job.get('title', 'N/A')}",
        f"Company: {job.get('company', 'N/A')}",
        f"Location: {job.get('location', 'N/A')}",
        f"Employment Type: {job.get('employment_type', 'N/A')}",
    ]
    if job.get("salary"):
        lines.append(f"Salary: {job['salary']}")
    desc = job.get("description", "")
    if desc:
        lines.append(f"Job Description:\n{desc[:2000]}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  COVER LETTER
# ─────────────────────────────────────────────
def generate_cover_letter(profile: dict, job: dict) -> str:
    """Generate a tailored cover letter using Gemini, with template fallback."""
    try:
        prompt = f"""Write a professional, tailored cover letter for the following job application.
Use the candidate's actual skills and experience — do NOT invent any experience they don't have.
Keep it concise (3-4 paragraphs), professional, and enthusiastic.
Do not use generic filler. Reference specific requirements from the job description.

CANDIDATE PROFILE:
{_profile_context(profile)}

JOB DETAILS:
{_job_context(job)}

Write the cover letter now. Start with "Dear Hiring Manager," and end with a professional sign-off using the candidate's name."""

        result = _call_gemini(prompt)
        if result:
            return result
    except Exception:
        pass  # Fall through to template

    # ── Template Fallback ──
    name   = profile.get("name", "Candidate")
    skills = profile.get("skills", "various technologies")
    title  = job.get("title", "the open position")
    company = job.get("company", "your company")

    return f"""Dear Hiring Manager,

I am writing to express my strong interest in the **{title}** position at **{company}**. With experience in {skills}, I am confident that my technical background aligns well with the requirements of this role.

Throughout my career, I have developed expertise that directly relates to the challenges described in this position. I am particularly excited about the opportunity to contribute to {company}'s team and bring my passion for building impactful solutions.

I would welcome the opportunity to discuss how my skills and experience can contribute to your team's success. Thank you for considering my application.

Best regards,
{name}"""


# ─────────────────────────────────────────────
#  RESUME SUMMARY
# ─────────────────────────────────────────────
def generate_resume_summary(profile: dict, job: dict) -> str:
    """Generate a tailored resume summary/profile section for a specific job."""
    try:
        prompt = f"""Write a professional resume summary/profile section (3-4 sentences) tailored to this specific job.
Use ONLY the candidate's real skills and experience — never invent or exaggerate.
Focus on how the candidate's background aligns with the job requirements.
Write in first person implied (no "I" — standard resume style).

CANDIDATE PROFILE:
{_profile_context(profile)}

JOB DETAILS:
{_job_context(job)}

Write the resume summary now. Output ONLY the summary text, no headers or labels."""

        result = _call_gemini(prompt)
        if result:
            return result
    except Exception:
        pass  # Fall through to template

    # ── Template Fallback ──
    skills = profile.get("skills", "").split(",")[:5]
    skills_str = ", ".join(s.strip() for s in skills if s.strip())
    exp = profile.get("experience_level", "")
    title = job.get("title", "software development")

    return (
        f"Results-driven professional with expertise in {skills_str}. "
        f"{'Experienced' if exp in ('mid','senior','lead') else 'Motivated'} "
        f"{'developer' if 'develop' in title.lower() or 'engineer' in title.lower() else 'professional'} "
        f"seeking to leverage technical skills and collaborative mindset in a {title} role. "
        f"Passionate about building scalable solutions and contributing to high-performing teams."
    )


# ─────────────────────────────────────────────
#  COLD EMAIL
# ─────────────────────────────────────────────
def generate_cold_email(profile: dict, job: dict) -> str:
    """Generate a cold outreach email for a job application."""
    try:
        prompt = f"""Write a concise, professional cold email to apply for a job opening.
The email should be direct, mention the specific role and company, highlight 2-3 relevant skills,
and express genuine interest. Keep it under 150 words. Use the candidate's real information only.

CANDIDATE PROFILE:
{_profile_context(profile)}

JOB DETAILS:
{_job_context(job)}

Write the email now. Include a subject line at the top formatted as "Subject: ..."."""

        result = _call_gemini(prompt)
        if result:
            return result
    except Exception:
        pass  # Fall through to template

    # ── Template Fallback ──
    name    = profile.get("name", "Candidate")
    skills  = profile.get("skills", "relevant technologies")
    title   = job.get("title", "the open position")
    company = job.get("company", "your company")

    return f"""Subject: Application for {title} — {name}

Hi,

I came across the {title} role at {company} and wanted to reach out directly. With hands-on experience in {skills}, I believe I'd be a strong fit for this position.

I'd love to learn more about the team and discuss how I can contribute. Would you be open to a brief call this week?

Best regards,
{name}"""


# ─────────────────────────────────────────────
#  KEY REQUIREMENTS EXTRACTOR
# ─────────────────────────────────────────────
def extract_key_requirements(job: dict) -> list[str]:
    """Extract 3-6 key requirements from a job's description and qualifications.
    NEVER raises — always returns a list of strings."""
    try:
        # Use highlights if available
        quals = job.get("qualifications", [])
        if quals and len(quals) >= 3:
            return quals[:6]

        # Otherwise extract from description
        desc = job.get("description", "")
        if not desc:
            return ["See full job description for requirements"]

        # Try Gemini first
        try:
            prompt = f"""Extract exactly 5 key requirements/qualifications from this job description.
Return them as a simple numbered list (1. ... 2. ... etc). Be concise — one line each.

{desc[:2000]}"""
            result = _call_gemini(prompt)
            if result:
                parsed = [re.sub(r'^\d+[\.)\]]\s*', '', line.strip())
                         for line in result.split('\n')
                         if line.strip() and re.match(r'^\d+[\.)\]]', line.strip())]
                if parsed:
                    return parsed[:6]
        except Exception:
            pass  # Fall through to text extraction

        # Fallback: simple bullet extraction
        bullets = re.findall(r'[•\-\*]\s*(.+?)(?:\n|$)', desc)
        if bullets:
            return [b.strip()[:100] for b in bullets[:6]]

        # Last resort: sentences
        sentences = [s.strip() for s in desc.split('.') if len(s.strip()) > 30]
        return [s[:100] for s in sentences[:5]] if sentences else ["Review the full job description for details"]

    except Exception:
        return ["Review the full job description for details"]


# ─────────────────────────────────────────────
#  FIT EXPLANATION
# ─────────────────────────────────────────────
def generate_fit_explanation(profile: dict, job: dict) -> str:
    """Generate a 1-2 sentence explanation of why this job fits the user.
    NEVER raises — always returns a string."""
    try:
        user_skills = set(s.strip().lower() for s in (profile.get("skills") or "").split(",") if s.strip())
        title       = job.get("title", "this role")
        company     = job.get("company", "this company")
        is_remote   = job.get("is_remote", False)
        reasons     = job.get("match_reasons", [])

        if reasons:
            return " ".join(reasons[:2])

        # Build from profile data
        parts = []
        from jobs_api import extract_skills_from_description
        job_skills = set(extract_skills_from_description(job.get("description", "")))
        overlap = user_skills & job_skills
        if overlap:
            parts.append(f"Your skills in {', '.join(sorted(overlap)[:3])} directly match this role's requirements.")
        if is_remote and "remote" in (profile.get("preferred_locations") or "").lower():
            parts.append("This is a remote position matching your location preference.")

        return " ".join(parts) if parts else f"This {title} role at {company} aligns with your career profile."

    except Exception:
        return f"This role aligns with your career profile."


# ─────────────────────────────────────────────
#  ADVANCED AI: SKILL GAP & COACHING
# ─────────────────────────────────────────────
def generate_skill_gap_analysis(profile: dict, job: dict) -> str:
    """Compare candidate profile against job description and output skill gaps and learning resources."""
    try:
        prompt = f"""As an expert career coach, perform a 'Skill Gap Analysis' for this candidate applying to this job.
1. Identify 2-3 specific skills the job requires that the candidate is missing.
2. For each missing skill, suggest exactly 1 free online resource or strategy to learn it.
3. Be encouraging and concise. Output in markdown format.

CANDIDATE PROFILE:
{_profile_context(profile)}

JOB DETAILS:
{_job_context(job)}

Analysis:"""
        result = _call_gemini(prompt)
        if result:
            return result
    except Exception:
        pass
    return "⚠️ Could not generate skill gap analysis right now. Please review the job requirements manually."


def generate_follow_up_email(profile: dict, job: dict) -> str:
    """Generate a polite follow-up email after applying."""
    try:
        prompt = f"""Write a polite, concise follow-up email for a candidate who applied to this job 5 days ago and hasn't heard back.
The tone should be professional and enthusiastic, not desperate. Max 100 words.

CANDIDATE:
{_profile_context(profile)}

JOB:
{_job_context(job)}

Email:"""
        result = _call_gemini(prompt)
        if result:
            return result
    except Exception:
        pass
    return f"Subject: Following up: Application for {job.get('title', 'Role')} at {job.get('company', 'Company')}\n\nHi Hiring Team,\n\nI hope you're having a great week. I wanted to briefly follow up on my application for the {job.get('title', 'open')} position. I remain very interested in the opportunity to join your team.\n\nPlease let me know if you need any additional information from me.\n\nBest regards,\n{profile.get('name', 'Candidate')}"


# ─────────────────────────────────────────────
#  HR TOOLS: BIAS DETECTION & CULTURE FIT
# ─────────────────────────────────────────────
def detect_job_bias(job_description: str) -> str:
    """Analyze a job description for biased, exclusionary, or overly aggressive language."""
    try:
        prompt = f"""As a Diversity & Inclusion (D&I) HR expert, review the following job description snippet.
Flag any gender-coded language (e.g., 'ninja', 'rockstar', 'aggressive'), ageist language, or overly demanding jargon that might discourage diverse applicants.
If it looks good, say '✅ The language is inclusive and professional.'
If you find bias, provide 2-3 bullet points on what to change.

Job Snippet:
{job_description[:2000]}

Analysis:"""
        result = _call_gemini(prompt)
        if result:
            return result
    except Exception:
        pass
    return "⚠️ Could not run bias detection right now."


def generate_culture_fit_questions(job_title: str, company: str) -> str:
    """Generate 3 behavioral/culture fit questions for HR to ask candidates."""
    try:
        prompt = f"""Generate 3 behavioral 'culture-fit' interview questions for a {job_title} role at {company}.
Focus on teamwork, adaptability, and problem-solving.
Format as a numbered list."""
        result = _call_gemini(prompt)
        if result:
            return result
    except Exception:
        pass
    return "1. Tell me about a time you had to adapt to a major change at work.\n2. How do you handle disagreements with team members?\n3. Describe a project where you had to learn a new skill on the fly."
# ─────────────────────────────────────────────
#  ADVANCED HR & CAREER TOOLS
# ─────────────────────────────────────────────
def generate_salary_negotiation_script(profile: dict, job: dict) -> str:
    """Generate a polite, professional salary negotiation script based on the profile and job."""
    try:
        prompt = f"""Write a professional and polite salary negotiation email script.
The candidate is responding to a job offer and wants to negotiate the base salary or overall compensation package.
Keep it under 150 words. Do not invent numbers if they aren't provided, just use placeholders like [Target Salary].

CANDIDATE: {_profile_context(profile)}
JOB: {_job_context(job)}"""
        result = _call_gemini(prompt)
        if result:
            return result
    except Exception:
        pass
    return "Hi [Hiring Manager Name],\n\nThank you so much for the offer for the [Job Title] position! I am very excited about the opportunity to join the team.\n\nBefore I sign, I would love to discuss the base salary. Given my experience and the current market rates for this role, I was hoping we could explore a starting salary closer to [Target Salary/Range].\n\nI am very enthusiastic about bringing my skills to the company and am open to discussing the overall compensation package.\n\nBest regards,\n[Your Name]"


def generate_onboarding_plan(candidate_name: str, job_title: str) -> str:
    """HR Tool: Generate a 30-60-90 day onboarding plan for a specific role."""
    try:
        prompt = f"""Generate a high-level 30-60-90 day onboarding plan for a new hire.
Candidate Name: {candidate_name}
Role: {job_title}

Structure it clearly with bullet points for Month 1 (30 days), Month 2 (60 days), and Month 3 (90 days).
Focus on integration, learning, and early wins."""
        result = _call_gemini(prompt)
        if result:
            return result
    except Exception:
        pass
    return f"**30-60-90 Day Plan for {candidate_name} ({job_title})**\n\n**First 30 Days (Learning):**\n- Complete HR onboarding and IT setup.\n- Meet team members and key stakeholders.\n- Review company documentation and architecture.\n\n**First 60 Days (Executing):**\n- Take on first small tasks or projects.\n- Shadow senior team members.\n- Establish regular 1:1 cadence with manager.\n\n**First 90 Days (Owning):**\n- Fully own a core responsibility or project.\n- Contribute proactively to team meetings.\n- Identify one process improvement."
