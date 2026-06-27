import fitz
import re
import os

# Defined skill categories with standardized casing mapping
SKILL_CATEGORIES_DB = {
    "Programming Languages": {
        "python": "Python", "javascript": "JavaScript", "sql": "SQL", "html": "HTML", "css": "CSS", 
        "java": "Java", "c++": "C++", "c#": "C#", "ruby": "Ruby", "go": "Go", "rust": "Rust", 
        "php": "PHP", "typescript": "TypeScript", "c": "C", "bash": "Bash", "shell": "Shell", 
        "r": "R", "scala": "Scala", "kotlin": "Kotlin", "swift": "Swift"
    },
    "Frameworks": {
        "flask": "Flask", "django": "Django", "fastapi": "FastAPI", "react": "React", 
        "angular": "Angular", "vue": "Vue", "bootstrap": "Bootstrap", "tailwind": "Tailwind", 
        "jquery": "jQuery", "node.js": "Node.js", "express": "Express", "spring boot": "Spring Boot", 
        "laravel": "Laravel", "next.js": "Next.js", "svelte": "Svelte"
    },
    "Databases": {
        "postgresql": "PostgreSQL", "mysql": "MySQL", "sqlite": "SQLite", "mongodb": "MongoDB", 
        "redis": "Redis", "faiss": "FAISS", "cassandra": "Cassandra", "oracle": "Oracle", 
        "mariadb": "MariaDB", "dynamodb": "DynamoDB", "elasticsearch": "Elasticsearch", "neo4j": "Neo4j"
    },
    "AI/ML": {
        "machine learning": "Machine Learning", "deep learning": "Deep Learning", "nlp": "NLP", 
        "langchain": "LangChain", "llama-index": "LlamaIndex", "huggingface": "HuggingFace", 
        "pytorch": "PyTorch", "tensorflow": "TensorFlow", "pandas": "Pandas", "numpy": "NumPy", 
        "scikit-learn": "Scikit-Learn", "keras": "Keras", "opencv": "OpenCV", "generative ai": "Generative AI", 
        "rag": "RAG", "llms": "LLMs"
    },
    "Cloud": {
        "aws": "AWS", "gcp": "GCP", "azure": "Azure", "docker": "Docker", "kubernetes": "Kubernetes",
        "lambda": "AWS Lambda", "ec2": "AWS EC2", "s3": "AWS S3"
    },
    "Tools": {
        "git": "Git", "linux": "Linux", "unix": "Unix", "restful apis": "RESTful APIs", 
        "postman": "Postman", "jira": "Jira", "confluence": "Confluence", "github": "GitHub", 
        "gitlab": "GitLab", "vscode": "VS Code"
    }
}

def extract_text(pdf_path):
    """
    Extracts raw text from a PDF resume file using PyMuPDF (fitz).
    """
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return ""

def parse_resume(pdf_path):
    """
    Extracts structured fields (Name, Contact Info, categorized skills, education,
    experience, projects, certifications, achievements) from a PDF resume.
    """
    # 0. Check parser cache using SHA-256 of the PDF file bytes
    cache_path = None
    try:
        import hashlib
        import json
        with open(pdf_path, "rb") as f:
            file_bytes = f.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        cache_dir = os.path.join("uploads", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"resume_{file_hash}.json")
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as cache_f:
                return json.load(cache_f)
    except Exception as e:
        print(f"Error checking resume cache: {e}")

    raw_text = extract_text(pdf_path)
    if not raw_text:
        return get_empty_candidate_profile()
        
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    # 1. Contact Information Extraction via Regex
    email = ""
    phone = ""
    linkedin = ""
    github = ""
    
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
    if email_match:
        email = email_match.group(0)
        
    phone_match = re.search(r"\+?\d[\d\-\s\(\)]{8,}\d", raw_text)
    if phone_match:
        phone = phone_match.group(0)
        
    linkedin_match = re.search(r"linkedin\.com/in/[\w\-]+", raw_text, re.IGNORECASE)
    if linkedin_match:
        linkedin = linkedin_match.group(0)
        
    github_match = re.search(r"github\.com/[\w\-]+", raw_text, re.IGNORECASE)
    if github_match:
        github = github_match.group(0)

    # 2. Extract Candidate Name
    # Fallback: Assume name is the first line unless it contains contact indicators
    name = "Candidate Profile"
    for line in lines[:5]:
        line_clean = line.strip()
        # Ensure it is not a contact line or too long
        if (len(line_clean) > 2 and 
            len(line_clean) < 30 and 
            "@" not in line_clean and 
            "phone" not in line_clean.lower() and 
            "+" not in line_clean and 
            "linkedin" not in line_clean.lower() and
            "github" not in line_clean.lower()):
            name = line_clean
            break

    # 3. Categorized Skills Extraction
    categorized_skills = {cat: [] for cat in SKILL_CATEGORIES_DB.keys()}
    all_extracted_skills = []
    lower_text = raw_text.lower()
    
    for category, skill_map in SKILL_CATEGORIES_DB.items():
        for skill_key, skill_display in skill_map.items():
            found = False
            # Special syntax matches (word boundaries vs exact substrings)
            if "+" in skill_key or "." in skill_key or " " in skill_key:
                if skill_key in lower_text:
                    found = True
            else:
                pattern = rf"\b{re.escape(skill_key)}\b"
                if re.search(pattern, lower_text):
                    found = True
            
            if found:
                categorized_skills[category].append(skill_display)
                all_extracted_skills.append(skill_display)
                
    # Sort categories to be clean
    for cat in categorized_skills:
        categorized_skills[cat] = sorted(list(set(categorized_skills[cat])))
    all_extracted_skills = sorted(list(set(all_extracted_skills)))

    # 4. Section Segmenting
    headers = {
        "education": ["education", "academic background", "qualification", "academic profile"],
        "experience": ["experience", "work experience", "employment history", "professional experience", "internship", "employment"],
        "projects": ["projects", "personal projects", "academic projects", "key projects", "achievements and projects"],
        "certifications": ["certifications", "licenses & certifications", "licenses and certifications", "certifications & licenses", "courses"],
        "achievements": ["achievements", "key achievements", "awards", "honors & awards", "honors and awards", "honors"]
    }
    
    # Track index of section headers in the lines list
    header_indices = []
    header_keywords_flat = []
    for section_name, keywords in headers.items():
        header_keywords_flat.extend(keywords)
        
    for idx, line in enumerate(lines):
        line_lower = line.lower().strip(":- ")
        for section_name, keywords in headers.items():
            if line_lower in keywords:
                header_indices.append((idx, section_name))
                break
                
    # Sort headers by order of appearance
    header_indices.sort(key=lambda x: x[0])
    
    sections_content = {
        "education": [],
        "experience": [],
        "projects": [],
        "certifications": [],
        "achievements": []
    }
    
    # Extract content strictly between header marks, omitting header strings themselves
    for i in range(len(header_indices)):
        start_idx, section_name = header_indices[i]
        end_idx = header_indices[i+1][0] if i + 1 < len(header_indices) else len(lines)
        
        # Sub-slice lines between these bounds
        section_lines = lines[start_idx+1 : end_idx]
        
        # Clean lines: remove standalone dividers or section headings that might trigger inside
        clean_section_lines = []
        for s_line in section_lines:
            s_line_lower = s_line.lower().strip(":- ")
            # Ignore duplicate subheaders if they show up in text blocks
            if s_line_lower in header_keywords_flat or re.match(r"^[-=_*·\s]+$", s_line):
                continue
            clean_section_lines.append(s_line)
            
        sections_content[section_name] = clean_section_lines

    # 5. Fallbacks for empty sections
    # Education fallback
    if not sections_content["education"]:
        edu_keywords = ["university", "college", "degree", "bachelor", "master", "b.tech", "m.tech", "gpa", "graduated", "school"]
        for line in lines:
            if any(kw in line.lower() for kw in edu_keywords):
                sections_content["education"].append(line)
                
    # Experience fallback
    if not sections_content["experience"]:
        exp_keywords = ["intern", "engineer", "developer", "analyst", "manager", "work", "experience", "inc.", "co."]
        for line in lines:
            if any(kw in line.lower() for kw in exp_keywords) and not any(ek in line.lower() for ek in ["university", "college", "degree", "project"]):
                sections_content["experience"].append(line)

    # Projects fallback
    if not sections_content["projects"]:
        proj_keywords = ["project", "built", "developed", "github.com", "utilizing"]
        for line in lines:
            if any(kw in line.lower() for kw in proj_keywords) and not any(ek in line.lower() for ek in ["experience", "intern", "university"]):
                sections_content["projects"].append(line)

    profile = {
        "name": name,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
        "skills": all_extracted_skills,
        "categorized_skills": categorized_skills,
        "education": sections_content["education"],
        "experience": sections_content["experience"],
        "projects": sections_content["projects"],
        "certifications": sections_content["certifications"],
        "achievements": sections_content["achievements"],
        "raw_text": raw_text
    }
    
    if cache_path:
        try:
            with open(cache_path, "w", encoding="utf-8") as cache_f:
                json.dump(profile, cache_f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving resume cache: {e}")
            
    return profile

def get_empty_candidate_profile():
    return {
        "name": "Candidate Profile",
        "email": "",
        "phone": "",
        "linkedin": "",
        "github": "",
        "skills": [],
        "categorized_skills": {cat: [] for cat in SKILL_CATEGORIES_DB.keys()},
        "education": [],
        "experience": [],
        "projects": [],
        "certifications": [],
        "achievements": [],
        "raw_text": ""
    }

if __name__ == "__main__":
    # Standard testing script execution
    sample_pdf = "sample_resume.pdf"
    if os.path.exists(sample_pdf):
        print(f"Parsing sample resume '{sample_pdf}'...")
        res = parse_resume(sample_pdf)
        print(f"Name: {res['name']}")
        print(f"Email: {res['email']}")
        print(f"Phone: {res['phone']}")
        print(f"LinkedIn: {res['linkedin']}")
        print(f"GitHub: {res['github']}")
        print("\nCategorized Skills:")
        for cat, list_skills in res["categorized_skills"].items():
            print(f"  {cat}: {list_skills}")
        print(f"\nCertifications: {res['certifications']}")
        print(f"Achievements: {res['achievements']}")
    else:
        print("Run generate_sample_resume.py to create testing PDF.")
