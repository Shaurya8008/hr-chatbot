import os
import json
import sqlite3
import math
import re
from abc import ABC, abstractmethod
from flask import Flask, request, jsonify, render_template
import PyPDF2
import io

app = Flask(__name__)

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTENTS_PATH = os.path.join(BASE_DIR, 'hr_intents.json')
DB_PATH = os.path.join(BASE_DIR, 'hr_database.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- OOP Architecture ---

class HRDatabase:
    """Interface for SQLite database operations."""
    def __init__(self, db_path):
        self.db_path = db_path

    def _query(self, query, params=(), fetchone=False):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetchone:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
        conn.close()
        return result

    def _execute(self, query, params=()):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        last_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return last_id

    def get_jobs(self, location=None, department=None):
        query = "SELECT * FROM jobs WHERE 1=1"
        params = []
        if location:
            query += " AND (location LIKE ? OR ? LIKE '%' || location || '%')"
            params.extend([f"%{location}%", location])
        if department:
            query += " AND (department LIKE ? OR ? LIKE '%' || department || '%')"
            params.extend([f"%{department}%", department])
        return self._query(query, tuple(params))

    def get_job_by_id(self, job_id):
        return self._query("SELECT * FROM jobs WHERE id = ?", (job_id,), fetchone=True)

    def get_job_by_title(self, title):
        clean_title = re.sub(r'[^\w\s]', '', title).lower()
        jobs = self._query("SELECT * FROM jobs")
        for job in jobs:
            clean_job_title = re.sub(r'[^\w\s]', '', job['title']).lower()
            if clean_title in clean_job_title or clean_job_title in clean_title:
                return job
        return None

    def create_application(self, name, email, position_id):
        return self._execute(
            "INSERT INTO applications (name, email, status, position_id) VALUES (?, ?, ?, ?)", 
            (name, email, "Pending Review", position_id)
        )

    def get_application_status(self, app_id):
        return self._query("SELECT * FROM applications WHERE id = ?", (app_id,), fetchone=True)

    def get_faq(self, category):
        return self._query("SELECT question, answer FROM faqs WHERE category LIKE ?", (f"%{category}%",))

    def save_profile(self, name, email, skills="", experience="", pref_loc="", pref_dept="", resume_text=""):
        existing = self._query("SELECT id FROM profiles WHERE email = ?", (email,), fetchone=True)
        if existing:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE profiles SET name=?, skills=?, experience=?, preferred_location=?, preferred_department=?, resume_text=? WHERE email=?",
                (name, skills, experience, pref_loc, pref_dept, resume_text, email)
            )
            conn.commit()
            conn.close()
            return existing['id']
        else:
            return self._execute(
                "INSERT INTO profiles (name, email, skills, experience, preferred_location, preferred_department, resume_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, email, skills, experience, pref_loc, pref_dept, resume_text)
            )

    def get_profile(self, email):
        return self._query("SELECT * FROM profiles WHERE email = ?", (email,), fetchone=True)

    def match_jobs_to_profile(self, profile):
        """Score all jobs against a profile's skills using keyword overlap."""
        profile_skills = set(s.strip().lower() for s in profile['skills'].split(',') if s.strip())
        profile_text = (profile['resume_text'] or '').lower()
        pref_loc = (profile['preferred_location'] or '').lower()
        pref_dept = (profile['preferred_department'] or '').lower()

        jobs = self._query("SELECT * FROM jobs")
        scored = []
        for job in jobs:
            job_skills = set(s.strip().lower() for s in job['skills'].split(',') if s.strip())
            job_desc_words = set(re.findall(r'\w+', job['description'].lower()))
            
            # Skill overlap score (primary)
            if profile_skills and job_skills:
                overlap = len(profile_skills & job_skills)
                skill_score = overlap / max(len(job_skills), 1)
            else:
                skill_score = 0

            # Resume text keyword match (secondary)
            resume_score = 0
            if profile_text:
                resume_words = set(re.findall(r'\w+', profile_text))
                resume_overlap = len(resume_words & job_skills) + len(resume_words & job_desc_words) * 0.3
                resume_score = min(resume_overlap / max(len(job_skills), 1), 0.5)

            # Location/department bonus
            loc_bonus = 0.1 if pref_loc and pref_loc in job['location'].lower() else 0
            dept_bonus = 0.1 if pref_dept and pref_dept in job['department'].lower() else 0

            total = min((skill_score * 0.7 + resume_score * 0.2 + loc_bonus + dept_bonus), 1.0)
            match_pct = int(total * 100)
            if match_pct > 10:
                scored.append({
                    'id': job['id'],
                    'title': job['title'],
                    'department': job['department'],
                    'location': job['location'],
                    'description': job['description'],
                    'skills': job['skills'],
                    'match': match_pct
                })

        scored.sort(key=lambda x: x['match'], reverse=True)
        return scored[:8]


class ResumeParser:
    """Parses PDF resumes and extracts skills and experience."""
    
    KNOWN_SKILLS = {
        'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue', 'node.js', 'nodejs',
        'flask', 'django', 'spring', 'express', 'sql', 'postgresql', 'mysql', 'mongodb', 'redis',
        'docker', 'kubernetes', 'aws', 'gcp', 'azure', 'terraform', 'jenkins', 'ci/cd', 'git',
        'html', 'css', 'sass', 'webpack', 'figma', 'sketch',
        'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'pandas', 'numpy',
        'data visualization', 'tableau', 'power bi', 'excel',
        'agile', 'scrum', 'jira', 'confluence',
        'rest api', 'graphql', 'microservices',
        'linux', 'bash', 'shell scripting',
        'selenium', 'test automation', 'api testing', 'performance testing',
        'communication', 'leadership', 'problem solving', 'teamwork',
        'sales', 'crm', 'negotiation', 'marketing', 'seo', 'content strategy',
        'financial modeling', 'accounting', 'budgeting', 'forecasting',
        'recruitment', 'talent management', 'employee relations',
        'technical writing', 'documentation',
        'computer vision', 'nlp', 'natural language processing',
        'r', 'scala', 'go', 'rust', 'c++', 'c#', 'swift', 'kotlin',
        'responsive design', 'accessibility', 'user research', 'wireframing', 'prototyping',
    }

    @staticmethod
    def extract_text_from_pdf(pdf_bytes):
        """Extract text from PDF file bytes."""
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text.strip()
        except Exception as e:
            return ""

    @classmethod
    def extract_skills(cls, text):
        """Match known skills against the resume text."""
        text_lower = text.lower()
        found = []
        for skill in cls.KNOWN_SKILLS:
            # Check multi-word skills first
            if skill in text_lower:
                found.append(skill)
        return list(set(found))

    @staticmethod
    def extract_experience(text):
        """Extract years of experience from resume text."""
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s+)?experience',
            r'experience\s*(?:of\s+)?(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?\s*(?:of\s+)?(?:exp|experience)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return f"{match.group(1)} years of experience"
        return "Experience not specified"

    @staticmethod
    def extract_name(text):
        """Try to extract name from top of resume."""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            # First non-empty line is often the name
            first_line = lines[0]
            if len(first_line) < 50 and not re.search(r'@|http|www|phone|address|resume|cv', first_line.lower()):
                return first_line
        return ""

    @staticmethod
    def extract_email(text):
        """Extract email from resume text."""
        match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
        return match.group(0) if match else ""


class NLUProcessor(ABC):
    """Abstract base class for Natural Language Understanding."""
    @abstractmethod
    def process(self, text):
        pass

class IntentClassifier(NLUProcessor):
    """Classifies user intent using keyword matching and word overlap."""
    def __init__(self, intents_file):
        with open(intents_file, 'r') as f:
            self.intents_data = json.load(f)['intents']

    def process(self, text):
        text = text.lower()
        scores = {}
        for intent_obj in self.intents_data:
            intent = intent_obj['intent']
            phrases = intent_obj['phrases']
            max_score = 0
            for phrase in phrases:
                phrase_words = set(re.findall(r'\w+', phrase.lower()))
                input_words = set(re.findall(r'\w+', text))
                if not input_words: continue
                overlap = len(phrase_words.intersection(input_words))
                score = overlap / len(input_words)
                if score > max_score:
                    max_score = score
            scores[intent] = max_score
        
        best_intent = max(scores, key=scores.get)
        if scores[best_intent] < 0.2:
            return "unknown"
        return best_intent

class EntityExtractor(NLUProcessor):
    """Extracts entities like application IDs or keywords from text."""
    def process(self, text):
        entities = {}
        ids = re.findall(r'\d+', text)
        entities["app_id"] = ids[0] if ids else None

        locations = ["india", "bangalore", "mumbai", "delhi", "san francisco", "new york", "london", "berlin", "remote", "singapore", "austin", "chicago"]
        departments = ["engineering", "human resources", "product", "design", "analytics", "marketing", "support", "sales", "finance"]
        titles = ["software engineer", "frontend developer", "backend developer", "hr specialist", "product manager", 
                  "ui/ux designer", "data scientist", "marketing lead", "customer success", "sales representative", 
                  "fullstack developer", "qa automation", "cloud architect", "sales executive", "finance analyst",
                  "devops engineer", "machine learning engineer", "technical writer"]

        text_lower = text.lower()
        for loc in locations:
            if loc in text_lower:
                entities["location"] = loc
                break
        
        for dept in departments:
            if dept in text_lower:
                entities["department"] = dept
                break

        for title in titles:
            if title in text_lower:
                entities["job_title"] = title
                break
                
        return entities


class ResponseGenerator:
    """Polymorphic response generator."""
    def text_response(self, text):
        return {"type": "text", "content": text}

    def card_response(self, title, items):
        return {"type": "card", "content": {"title": title, "items": items}}

    def form_response(self, fields):
        return {"type": "form", "content": fields}

    def job_list_response(self, title, jobs):
        """Returns clickable job listing cards."""
        job_data = []
        for j in jobs:
            entry = {
                "id": j['id'] if isinstance(j, dict) else j['id'],
                "title": j['title'],
                "location": j['location'],
                "department": j['department']
            }
            if isinstance(j, dict) and 'match' in j:
                entry['match'] = j['match']
            job_data.append(entry)
        return {"type": "job_list", "content": {"title": title, "jobs": job_data}}

    def job_detail_response(self, job):
        """Returns a detailed job view with Apply action."""
        return {"type": "job_detail", "content": {
            "id": job['id'],
            "title": job['title'],
            "department": job['department'],
            "location": job['location'],
            "description": job['description'],
            "skills": job['skills']
        }}


class Person(ABC):
    """Abstract person class with encapsulated private fields."""
    def __init__(self, name, email):
        self.__name = name
        self.__email = email

    @property
    def name(self):
        return self.__name

    @property
    def email(self):
        return self.__email

class Candidate(Person):
    def __init__(self, name, email, application_id=None):
        super().__init__(name, email)
        self.__application_id = application_id

    @property
    def application_id(self):
        return self.__application_id

class Employee(Person):
    def __init__(self, name, email, employee_id=None):
        super().__init__(name, email)
        self.__employee_id = employee_id

class DialogManager:
    """Tracks conversation state and user mode."""
    def __init__(self):
        self.mode = "candidate"
        self.context = {}

    def set_mode(self, mode):
        self.mode = mode

    def get_mode(self):
        return self.mode


class HRChatBot:
    """Main controller class orchestrating the chatbot components."""
    def __init__(self):
        self.db = HRDatabase(DB_PATH)
        self.classifier = IntentClassifier(INTENTS_PATH)
        self.extractor = EntityExtractor()
        self.generator = ResponseGenerator()
        self.dialog = DialogManager()
        self.resume_parser = ResumeParser()

    def handle_message(self, text, current_mode="candidate", user_email=None):
        self.dialog.set_mode(current_mode)
        intent = self.classifier.process(text)
        entities = self.extractor.process(text)
        
        if intent == "greet":
            return self.generator.text_response(
                f"Hello! I'm your HR Assistant in **{current_mode}** mode. "
                "I can help you with:\n• Browse & search job openings\n• View job details\n"
                "• Upload your resume (PDF) for smart job matching\n• Apply to positions\n"
                "• Check application status\n• HR policy questions\n\nHow can I help?"
            )
        
        elif intent == "farewell":
            return self.generator.text_response("Goodbye! Have a great day ahead. 🎉")

        elif intent == "job_openings":
            loc = entities.get("location")
            dept = entities.get("department")
            jobs = self.db.get_jobs(location=loc, department=dept)
            
            if not jobs:
                jobs = self.db.get_jobs()
                if not jobs:
                    return self.generator.text_response("No job openings are currently available.")
                title = "All Available Job Openings"
            else:
                title = "Job Openings"
                if loc or dept:
                    parts = []
                    if dept: parts.append(dept.title())
                    if loc: parts.append("in " + loc.title())
                    title += " " + " ".join(parts)
            
            return self.generator.job_list_response(title, jobs)

        elif intent == "job_details":
            title_query = entities.get("job_title")
            if title_query:
                job = self.db.get_job_by_title(title_query)
                if job:
                    return self.generator.job_detail_response(job)
                return self.generator.text_response(f"I couldn't find details for '{title_query}'.")
            return self.generator.text_response("Which job role would you like to know more about? Click a job from the listings, or type a role name.")

        elif intent == "check_status":
            app_id = entities.get("app_id")
            if app_id:
                status = self.db.get_application_status(app_id)
                if status:
                    return self.generator.text_response(
                        f"📋 **Application #{app_id}**\n"
                        f"• **Name**: {status['name']}\n"
                        f"• **Status**: {status['status']}"
                    )
                return self.generator.text_response(f"Sorry, I couldn't find application #{app_id}.")
            
            # If no ID, but we have email, show most recent application
            if user_email:
                conn = sqlite3.connect(self.db.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM applications WHERE email = ? ORDER BY id DESC LIMIT 1", (user_email,))
                status = cursor.fetchone()
                conn.close()
                if status:
                    return self.generator.text_response(
                        f"📋 **Your Latest Application (#{status['id']})**\n"
                        f"• **Position ID**: {status['position_id']}\n"
                        f"• **Status**: {status['status']}"
                    )
            return self.generator.text_response("Please provide your Application ID (e.g., 'status of 123').")

        elif intent == "leave_policy":
            faqs = self.db.get_faq("policy")
            if faqs:
                return self.generator.text_response(faqs[0]['answer'])
            return self.generator.text_response("Our leave policy allows for 25 days of annual leave.")

        elif intent == "salary_info":
            if current_mode == "candidate":
                return self.generator.text_response("Salary details vary by role. Please check individual job listings for ranges.")
            return self.generator.text_response("Salaries are credited on the last working day of the month. You can view your payslip on the employee portal.")

        elif intent == "onboarding_faq":
            return self.generator.text_response("For onboarding, please ensure you have your ID, educational certificates, and tax documents ready. Joining dates are specified in your offer letter.")

        elif intent == "resignation_process":
            if current_mode == "candidate":
                return self.generator.text_response("This information is only available for active employees.")
            return self.generator.text_response("To resign, you must submit a formal notice to your manager. The standard notice period is 30 days.")

        elif intent == "apply_job":
            return self.generator.form_response(["Full Name", "Email Address", "Position ID"])

        elif intent == "save_resume":
            return self.generator.text_response(
                "📎 To upload your resume, click the **📎 Upload Resume** button below the chat input. "
                "I'll extract your skills from the PDF and match you with the best roles!"
            )

        elif intent == "suggest_jobs":
            email = user_email
            if email:
                profile = self.db.get_profile(email)
                if profile:
                    matches = self.db.match_jobs_to_profile(profile)
                    if matches:
                        return self.generator.job_list_response(
                            f"🎯 Jobs Matching Your Profile ({len(matches)} found)",
                            matches
                        )
            return self.generator.text_response(
                "To get personalized job suggestions, please upload your resume first using the **📎 Upload Resume** button. "
                "I'll analyze your skills and recommend the best matching positions!"
            )

        elif intent == "schedule_interview" or intent == "reschedule_interview":
            return self.generator.text_response("To schedule or reschedule an interview, please check the invite email you received and use the Calendly link provided.")

        return self.generator.text_response("I'm not sure I understand. Could you rephrase that? You can ask about job openings, application status, upload your resume, or HR policies.")


# --- Flask Routes ---

bot = HRChatBot()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    mode = data.get('mode', 'candidate')
    email = data.get('email')
    response = bot.handle_message(message, mode, email)
    return jsonify(response)

@app.route('/job/<int:job_id>', methods=['GET'])
def get_job(job_id):
    job = bot.db.get_job_by_id(job_id)
    if job:
        return jsonify(bot.generator.job_detail_response(job))
    return jsonify({"type": "text", "content": "Job not found."}), 404

@app.route('/submit_application', methods=['POST'])
def submit_application():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    pos_id = data.get('position_id')
    
    job = bot.db.get_job_by_id(pos_id)
    job_title = job['title'] if job else f"Position #{pos_id}"
    
    app_id = bot.db.create_application(name, email, pos_id)
    return jsonify(f"✅ Application submitted successfully!\n\n• **Application ID**: {app_id}\n• **Position**: {job_title}\n• **Status**: Pending Review\n\nUse your ID to track progress: *\"Check status of {app_id}\"*")

@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({"type": "text", "content": "No file uploaded. Please select a PDF file."}), 400
    
    file = request.files['resume']
    if not file.filename.endswith('.pdf'):
        return jsonify({"type": "text", "content": "Please upload a PDF file only."}), 400
    
    # Read and parse the PDF
    pdf_bytes = file.read()
    resume_text = ResumeParser.extract_text_from_pdf(pdf_bytes)
    
    if not resume_text:
        return jsonify({"type": "text", "content": "Could not extract text from this PDF. Please ensure it's not a scanned image."}), 400
    
    # Extract information
    skills = ResumeParser.extract_skills(resume_text)
    experience = ResumeParser.extract_experience(resume_text)
    name = ResumeParser.extract_name(resume_text)
    email = ResumeParser.extract_email(resume_text)
    
    skills_str = ", ".join(skills)
    
    # Save profile
    if email:
        profile_id = bot.db.save_profile(
            name=name or "Candidate",
            email=email,
            skills=skills_str,
            experience=experience,
            resume_text=resume_text[:2000]  # Store first 2000 chars
        )
    
    # Match jobs
    if email:
        profile = bot.db.get_profile(email)
        if profile:
            matches = bot.db.match_jobs_to_profile(profile)
            if matches:
                return jsonify(bot.generator.job_list_response(
                    f"🎯 Jobs Matching Your Resume ({len(matches)} found)",
                    matches
                ))
    
    # Fallback: return skills found even without email
    if skills:
        return jsonify({
            "type": "text",
            "content": f"📄 **Resume Analyzed!**\n\n"
                       f"**Skills Found**: {skills_str}\n"
                       f"**Experience**: {experience}\n\n"
                       f"I couldn't find an email in your resume to save the profile. "
                       f"Please type your email in the chat so I can match you with jobs."
        })
    
    return jsonify({"type": "text", "content": "I couldn't extract meaningful skills from this resume. Please ensure it contains readable text."})

@app.route('/auto_apply', methods=['POST'])
def auto_apply():
    data = request.json
    email = data.get('email')
    job_id = data.get('job_id')
    
    if not email or not job_id:
        return jsonify({"type": "text", "content": "Missing email or job ID for auto-apply."}), 400
    
    profile = bot.db.get_profile(email)
    if not profile:
        return jsonify({"type": "text", "content": "No saved profile found. Please upload your resume first."})
    
    job = bot.db.get_job_by_id(job_id)
    if not job:
        return jsonify({"type": "text", "content": "Job not found."}), 404
    
    app_id = bot.db.create_application(profile['name'], profile['email'], job_id)
    return jsonify(
        f"🚀 **Auto-Applied Successfully!**\n\n"
        f"• **Application ID**: {app_id}\n"
        f"• **Position**: {job['title']}\n"
        f"• **Location**: {job['location']}\n"
        f"• **Status**: Pending Review\n\n"
        f"Check your status: *\"Status of {app_id}\"*"
    )


if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
