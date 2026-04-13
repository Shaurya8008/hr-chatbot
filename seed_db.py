import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'hr_database.db')

def seed():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        department TEXT NOT NULL,
        location TEXT NOT NULL,
        description TEXT NOT NULL,
        skills TEXT NOT NULL DEFAULT ''
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        status TEXT NOT NULL,
        position_id INTEGER,
        FOREIGN KEY (position_id) REFERENCES jobs (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS faqs (
        category TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        skills TEXT DEFAULT '',
        experience TEXT DEFAULT '',
        preferred_location TEXT DEFAULT '',
        preferred_department TEXT DEFAULT '',
        resume_text TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Seed Jobs (with skill tags)
    jobs = [
        ('Software Engineer', 'Engineering', 'Remote', 
         'Develop and maintain scalable web applications using modern frameworks.',
         'python, javascript, react, node.js, sql, git, docker, rest api'),
        ('Frontend Developer', 'Engineering', 'San Francisco', 
         'Create beautiful and interactive UIs with modern JS frameworks.',
         'javascript, react, typescript, css, html, figma, webpack, responsive design'),
        ('Backend Developer', 'Engineering', 'New York', 
         'Architect robust APIs and databases for high-traffic services.',
         'python, java, sql, postgresql, redis, docker, microservices, rest api'),
        ('HR Specialist', 'Human Resources', 'London', 
         'Manage recruitment pipelines and employee relations programs.',
         'recruitment, employee relations, hris, compliance, communication, talent management'),
        ('Product Manager', 'Product', 'Remote', 
         'Define product vision, strategy, and roadmap with data-driven decisions.',
         'product strategy, roadmap, agile, scrum, analytics, user research, stakeholder management'),
        ('UI/UX Designer', 'Design', 'Berlin', 
         'Design user-centric experiences across web and mobile platforms.',
         'figma, sketch, user research, wireframing, prototyping, design systems, accessibility'),
        ('Data Scientist', 'Analytics', 'Singapore', 
         'Analyze complex datasets and build ML models for business insights.',
         'python, machine learning, tensorflow, pandas, sql, statistics, data visualization, r'),
        ('Marketing Lead', 'Marketing', 'Austin', 
         'Drive user acquisition and brand awareness through multi-channel campaigns.',
         'digital marketing, seo, google analytics, content strategy, social media, campaign management'),
        ('Customer Success', 'Support', 'Remote', 
         'Help users achieve their goals and drive product adoption.',
         'customer support, communication, crm, problem solving, onboarding, retention'),
        ('Sales Representative', 'Sales', 'Chicago', 
         'Identify new business opportunities and manage client relationships.',
         'sales, crm, negotiation, pipeline management, cold calling, b2b, presentation'),
        ('Fullstack Developer', 'Engineering', 'Bangalore', 
         'Modern fullstack development with Python and React for enterprise apps.',
         'python, react, javascript, flask, django, postgresql, docker, aws, rest api'),
        ('QA Automation Engineer', 'Engineering', 'Mumbai', 
         'Build automated testing frameworks for high-traffic applications.',
         'selenium, python, java, test automation, ci/cd, jenkins, api testing, performance testing'),
        ('Cloud Architect', 'Engineering', 'India', 
         'Design robust cloud architectures for global clients using AWS/GCP.',
         'aws, gcp, azure, terraform, kubernetes, docker, cloud security, networking, python'),
        ('Sales Executive', 'Sales', 'Delhi', 
         'Expand our presence in the Indian market with enterprise deals.',
         'sales, b2b, enterprise sales, negotiation, crm, pipeline management, presentation'),
        ('Finance Analyst', 'Finance', 'Mumbai', 
         'Financial modeling, reporting, and strategic forecasting.',
         'excel, financial modeling, sql, tableau, accounting, forecasting, budgeting'),
        ('DevOps Engineer', 'Engineering', 'Bangalore', 
         'Build and maintain CI/CD pipelines and cloud infrastructure.',
         'docker, kubernetes, aws, terraform, jenkins, linux, python, monitoring, ci/cd'),
        ('Machine Learning Engineer', 'Engineering', 'Remote', 
         'Deploy production ML models and build data pipelines at scale.',
         'python, tensorflow, pytorch, mlops, docker, aws, sql, deep learning, computer vision'),
        ('Technical Writer', 'Product', 'Remote', 
         'Create developer documentation, API guides, and technical content.',
         'technical writing, api documentation, markdown, git, developer tools, communication')
    ]
    cursor.executemany('INSERT INTO jobs (title, department, location, description, skills) VALUES (?, ?, ?, ?, ?)', jobs)

    # Seed Applications
    applications = [
        ('Alice Smith', 'alice@example.com', 'Interview Scheduled', 1),
        ('Bob Johnson', 'bob@example.com', 'Under Review', 2),
        ('Charlie Brown', 'charlie@example.com', 'Offer Extended', 3),
        ('Diana Prince', 'diana@example.com', 'Rejected', 4),
        ('Ethan Hunt', 'ethan@example.com', 'Pending Review', 5)
    ]
    cursor.executemany('INSERT INTO applications (name, email, status, position_id) VALUES (?, ?, ?, ?)', applications)

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
