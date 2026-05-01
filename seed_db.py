import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'hr_database.db')

def seed():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Applications table — tracks jobs user has bookmarked/applied to
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        status TEXT NOT NULL,
        job_api_id TEXT,
        job_title TEXT DEFAULT '',
        job_company TEXT DEFAULT '',
        job_location TEXT DEFAULT '',
        apply_link TEXT DEFAULT '',
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Extended profiles table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        skills TEXT DEFAULT '',
        tech_stack TEXT DEFAULT '',
        experience_level TEXT DEFAULT '',
        preferred_roles TEXT DEFAULT '',
        preferred_locations TEXT DEFAULT '',
        salary_min INTEGER DEFAULT 0,
        salary_max INTEGER DEFAULT 0,
        salary_currency TEXT DEFAULT 'USD',
        notice_period TEXT DEFAULT '',
        resume_text TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Bookmarked / saved jobs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS saved_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        job_api_id TEXT NOT NULL,
        job_title TEXT DEFAULT '',
        job_company TEXT DEFAULT '',
        job_location TEXT DEFAULT '',
        apply_link TEXT DEFAULT '',
        saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(email, job_api_id)
    )
    ''')

    # FAQs — retained
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS faqs (
        category TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL
    )
    ''')

    # Seed FAQs
    faqs = [
        ('Policy', 'What is the leave policy?', 'Employees are entitled to 25 days of paid annual leave plus public holidays.'),
        ('Salary', 'When is the salary credited?', 'Salaries are processed on the last working day of every month.'),
        ('Onboarding', 'What documents are required for joining?', 'You need to provide your ID proof, educational certificates, and previous employment records.'),
        ('Onboarding', 'Is there a dress code?', 'Our office follows a smart casual dress code policy.'),
        ('Resignation', 'What is the notice period?', 'The standard notice period is 30 days for all employees.')
    ]
    cursor.executemany('INSERT INTO faqs (category, question, answer) VALUES (?, ?, ?)', faqs)

    conn.commit()
    conn.close()
    print(f"Database seeded successfully at {DB_PATH}")

if __name__ == "__main__":
    seed()
