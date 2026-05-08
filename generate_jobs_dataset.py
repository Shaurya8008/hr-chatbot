import csv
import random

TITLES = [
    "Software Engineer", "Data Scientist", "Product Manager", "DevOps Engineer", 
    "Frontend Developer", "Backend Developer", "Full Stack Developer", "Machine Learning Engineer",
    "Cloud Architect", "UI/UX Designer", "Data Analyst", "Systems Administrator"
]

COMPANIES = [
    "TechCorp", "InnoSoft", "DataWorks", "Cloud9", "NextGen Solutions",
    "Alpha Systems", "Beta Technologies", "Gamma Innovations", "Delta Software", "Epsilon IT"
]

SKILLS_POOL = [
    "python", "javascript", "react", "sql", "aws", "docker", "kubernetes",
    "java", "c++", "machine learning", "tensorflow", "pytorch", "nodejs", "typescript",
    "html", "css", "agile", "scrum", "git", "linux", "bash", "rest api", "graphql", "flask", "django"
]

def generate_description(title, skills):
    return f"We are looking for a talented {title} to join our team. You will be responsible for building scalable systems and working with cross-functional teams. Required skills include {', '.join(skills)}. The ideal candidate has strong problem-solving abilities and a passion for technology."

def main():
    print("Generating jobs_dataset.csv...")
    with open("jobs_dataset.csv", "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["job_id", "title", "company", "description", "skills"])
        
        for i in range(1, 201):  # Generate 200 jobs
            title = random.choice(TITLES)
            company = random.choice(COMPANIES)
            num_skills = random.randint(3, 8)
            skills = random.sample(SKILLS_POOL, num_skills)
            desc = generate_description(title, skills)
            
            writer.writerow([f"JOB_{i:03d}", title, company, desc, ",".join(skills)])
            
    print("Successfully generated 200 jobs in jobs_dataset.csv")

if __name__ == "__main__":
    main()
