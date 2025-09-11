import json
import random

# Example skill pools
skills_pool = [
    # Programming
    "Python", "Java", "C++", "C#", "JavaScript", "TypeScript", "Go", "Rust", "Ruby", "PHP",
    
    # Web/Frontend
    "React", "Angular", "Vue.js", "Next.js", "HTML", "CSS", "TailwindCSS", "Bootstrap",
    
    # Backend / APIs
    "Node.js", "Express.js", "Spring Boot", "Django", "Flask", "FastAPI", "GraphQL",
    
    # Databases
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Cassandra", "Elasticsearch",
    
    # DevOps / Cloud
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Terraform", "Ansible", "Jenkins", "GitHub Actions",
    
    # Data Science / ML
    "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy", "Matplotlib", "Seaborn", "R", "MATLAB",
    
    # Big Data / Streaming
    "Hadoop", "Spark", "Kafka", "Airflow", "Snowflake", "Databricks",
    
    # Other
    "Linux", "Git", "Figma", "Tableau", "PowerBI", "JIRA", "Confluence"
]

strengths_pool = [
    "Strong backend system design skills",
    "Excellent problem-solving and debugging ability",
    "Good understanding of cloud-native architecture",
    "Experience working with distributed systems",
    "Strong foundations in data structures and algorithms",
    "Hands-on experience with microservices",
    "Excellent leadership and team mentoring skills",
    "Experience in building CI/CD pipelines",
    "Strong knowledge of frontend frameworks",
    "Excellent written and verbal communication",
    "Good experience with API development and integration",
    "Experience managing scalable databases",
    "Proven ability to deliver under tight deadlines",
    "Good understanding of containerization",
    "Experience with real-time data processing",
    "Exposure to MLOps practices",
    "Strong analytical and quantitative skills",
    "Good ability to work cross-functionally",
    "Experience with Agile methodologies",
    "Excellent troubleshooting of production systems"
]


recommendations_pool = [
    "Gain hands-on experience with Kubernetes",
    "Get certified in AWS or Azure cloud services",
    "Learn advanced React and modern frontend patterns",
    "Improve understanding of data pipelines with Airflow",
    "Work on personal projects involving Docker",
    "Strengthen knowledge of CI/CD automation tools",
    "Contribute to open-source projects in Python",
    "Learn advanced SQL optimization techniques",
    "Explore distributed systems concepts",
    "Gain more exposure to real-time data streaming",
    "Improve deployment practices with Terraform",
    "Take a course in machine learning model deployment",
    "Work on optimizing large-scale database systems",
    "Practice designing scalable system architectures",
    "Gain practical experience with Spark and Hadoop",
    "Take certification in project management methodologies",
    "Focus on improving UI/UX design knowledge",
    "Deepen understanding of data visualization with Tableau",
    "Build projects using Flask or FastAPI",
    "Learn more about monitoring and observability tools"
]


def generate_example(i):
    # Randomly sample skills
    resume_skills = random.sample(skills_pool, k=random.randint(3,6))
    job_skills = random.sample(skills_pool, k=random.randint(3,6))

    # Compute matches
    matched = [s for s in resume_skills if s in job_skills]
    missing = [s for s in job_skills if s not in resume_skills]

    # Fake score based on overlap
    score = int((len(matched) / max(1, len(job_skills))) * 100)

    # Build synthetic example
    return {
        "messages": [
            {
                "role": "system",
                "content": "You are an expert recruiter assistant that evaluates resumes against job descriptions."
            },
            {
                "role": "user",
                "content": f"Resume Skills: {', '.join(resume_skills)}\n"
                           f"Resume Summary: Candidate with experience in {', '.join(random.sample(skills_pool, 2))}.\n"
                           f"Job Skills: {', '.join(job_skills)}\n"
                           f"Job Description: Looking for an engineer with strong skills in {', '.join(job_skills)}."
            },
            {
                "role": "assistant",
                "content": f"Match Score: {score}%\n"
                           f"Matched Skills: {', '.join(matched) if matched else 'None'}\n"
                           f"Missing Skills: {', '.join(missing) if missing else 'None'}\n"
                           f"Strengths: {random.choice(strengths_pool)}\n"
                           f"Recommendation: {random.choice(recommendations_pool)}"
            }
        ]
    }

# Generate 200 examples
dataset = [generate_example(i) for i in range(2000)]

# Save to JSONL
with open("dataset.jsonl", "w", encoding="utf-8") as f:
    for item in dataset:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print("✅ Generated dataset.jsonl with 1000 examples")
