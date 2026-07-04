import json
import re
import os
import logging
import hashlib
from typing import Any
from rag import retrieve_context
from granite import generate_response

# Configure Logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global Cache Directory
CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads", "cache"))
os.makedirs(CACHE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Company-specific interview profile configurations
# ---------------------------------------------------------------------------
COMPANY_PROFILES: dict[str, dict[str, Any]] = {
    "IBM": {
        "focus": "enterprise hybrid-cloud solutions, AI/ML integration with watsonx, responsible AI, and open-source innovation",
        "values": "Think, IBM Garage methodology, growth mindset, client obsession",
        "tech_stack": "IBM Cloud, watsonx.ai, Red Hat OpenShift, Kubernetes, Java, Python",
        "style": "structured behavioural (STAR), case studies, system architecture",
        "difficulty_boost": 0,
    },
    "Google": {
        "focus": "algorithmic problem solving, scalable system design, data structures, and Googleyness",
        "values": "user focus, innovation, collaboration, learning agility",
        "tech_stack": "Python, Go, C++, GCP, Kubernetes, BigQuery, TensorFlow",
        "style": "LeetCode-style coding, system design, behavioural leadership principles",
        "difficulty_boost": 5,
    },
    "Microsoft": {
        "focus": "cloud-first engineering, Azure services, inclusive design, and product thinking",
        "values": "growth mindset, customer empathy, diversity and inclusion",
        "tech_stack": "Azure, C#, .NET, Python, TypeScript, Power Platform",
        "style": "coding challenges, system design, product sense, behavioural",
        "difficulty_boost": 3,
    },
    "Amazon": {
        "focus": "AWS expertise, operational excellence, leadership principles, and customer obsession",
        "values": "16 Leadership Principles (customer obsession, bias for action, ownership, invent and simplify)",
        "tech_stack": "AWS, Java, Python, DynamoDB, Lambda, SQS, Kafka",
        "style": "STAR-heavy behavioural tied to Leadership Principles, coding, system design",
        "difficulty_boost": 5,
    },
    "TCS": {
        "focus": "enterprise application development, IT services delivery, and client engagement",
        "values": "integrity, excellence, innovation, collaborative work",
        "tech_stack": "Java, Python, SQL, SAP, Mainframes, AWS, Azure",
        "style": "technical aptitude, programming fundamentals, verbal communication",
        "difficulty_boost": -5,
    },
    "Infosys": {
        "focus": "digital transformation, IT consulting, software services, and process automation",
        "values": "learning agility, client delivery, continuous improvement",
        "tech_stack": "Java, Python, .NET, SQL, AWS, Azure, RPA",
        "style": "aptitude tests, programming concepts, verbal reasoning, HR interview",
        "difficulty_boost": -5,
    },
    "Accenture": {
        "focus": "technology consulting, digital strategy, cloud migration, and intelligent automation",
        "values": "client value, stewardship, best people, continuous learning",
        "tech_stack": "Java, Python, SAP, Salesforce, AWS, Azure, RPA",
        "style": "case interviews, technical concepts, values-based behavioural",
        "difficulty_boost": -3,
    },
    "Wipro": {
        "focus": "IT services, digital transformation, and enterprise software delivery",
        "values": "integrity, responsiveness, innovation, human spirit",
        "tech_stack": "Java, Python, C#, SQL, Hadoop, AWS, Azure",
        "style": "technical MCQ, coding fundamentals, HR fit questions",
        "difficulty_boost": -5,
    },
}

DEFAULT_COMPANY_PROFILE: dict[str, Any] = {
    "focus": "software engineering best practices and general technical knowledge",
    "values": "teamwork, innovation, continuous learning",
    "tech_stack": "Python, SQL, Git, Docker, REST APIs",
    "style": "technical and behavioural",
    "difficulty_boost": 0,
}

# Behavioural competency categories for Phase 2.3
BEHAVIOURAL_COMPETENCIES = [
    "Leadership",
    "Teamwork",
    "Communication",
    "Conflict Resolution",
    "Time Management",
    "Problem Solving",
    "Adaptability",
]

def get_cache(key_str):
    """
    Retrieves cached JSON object if it exists.
    """
    try:
        key_hash = hashlib.sha256(key_str.encode("utf-8")).hexdigest()
        cache_path = os.path.join(CACHE_DIR, f"{key_hash}.json")
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                logging.info(f"Report Cache Hit: {key_hash}")
                return json.load(f)
    except Exception as e:
        logging.error(f"Error reading cache: {e}")
    return None

def set_cache(key_str, data):
    """
    Saves JSON object to cache.
    """
    try:
        key_hash = hashlib.sha256(key_str.encode("utf-8")).hexdigest()
        cache_path = os.path.join(CACHE_DIR, f"{key_hash}.json")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            logging.info(f"Report Cache Saved: {key_hash}")
    except Exception as e:
        logging.error(f"Error writing cache: {e}")

def generate_skill_breakdown_chart(score_breakdown, candidate_name):
    """
    Generates a horizontal bar chart of the skill categories score breakdown
    using Matplotlib, styled specifically for the minimal Light SaaS theme.
    """
    try:
        import matplotlib
        matplotlib.use('Agg') # Non-interactive backend for server environments
        import matplotlib.pyplot as plt
        
        # Format candidate name for filename
        safe_name = re.sub(r'\W+', '_', candidate_name.lower())
        charts_dir = os.path.join("static", "charts")
        os.makedirs(charts_dir, exist_ok=True)
        chart_path = os.path.join(charts_dir, f"skills_{safe_name}.png")
        
        categories = list(score_breakdown.keys())
        scores = list(score_breakdown.values())
        
        # Light Theme Minimal Styling
        fig, ax = plt.subplots(figsize=(6.5, 3.2), facecolor='#ffffff')
        ax.set_facecolor('#ffffff')
        
        # Draw Bars using palette: Emerald Green (High), Indigo (Medium), Amber Orange (Low)
        colors = ['#10b981' if s >= 85 else '#6366f1' if s >= 65 else '#f59e0b' for s in scores]
        bars = ax.barh(categories, scores, color=colors, height=0.52, edgecolor='none')
        
        # Formatting axes
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#e2e8f0')
        ax.spines['left'].set_color('#e2e8f0')
        ax.tick_params(colors='#475569', labelsize=9)
        ax.set_xlim(0, 100)
        
        # Gridlines
        ax.grid(axis='x', linestyle='--', alpha=0.5, color='#e2e8f0')
        ax.set_axisbelow(True)
        
        # Add labels on top of the bars
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 2, bar.get_y() + bar.get_height()/2, f'{int(width)}%', 
                    va='center', ha='left', color='#0f172a', fontweight='bold', fontsize=9)
            
        plt.title("Skill Alignment Breakdown", color='#0f172a', fontsize=11, fontweight='bold', pad=12, loc='left')
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close()
        
        return f"charts/skills_{safe_name}.png"
    except Exception as e:
        logging.error(f"Error generating matplotlib skill chart: {e}")
        print(f"Error generating matplotlib skill chart: {e}")
        return ""

def calculate_weighted_score(candidate_data, job_role, experience_level, company):
    """
    Performs a deterministic Python-based baseline weighted score calculation
    based on parsed resume quality, certifications, skills counts, and projects.
    """
    skills = candidate_data.get("skills", [])
    projects = candidate_data.get("projects", [])
    education = candidate_data.get("education", [])
    experience = candidate_data.get("experience", [])
    certifications = candidate_data.get("certifications", [])
    cat_skills = candidate_data.get("categorized_skills", {})
    
    # 1. Category-specific breakdown scoring
    breakdown = {}
    for cat in ["Programming Languages", "Frameworks", "Databases", "AI/ML", "Cloud", "Tools"]:
        items = cat_skills.get(cat, [])
        if not items:
            score = 35
        elif len(items) == 1:
            score = 65
        elif len(items) == 2:
            score = 85
        else:
            score = 100
        breakdown[cat] = score
        
    # 2. General baseline score weights
    skills_weight = min(len(skills) * 8, 100) * 0.25
    projects_weight = min(len(projects) * 35, 100) * 0.15
    exp_weight = min(len(experience) * 20, 100) * 0.15
    edu_weight = 100 * 0.10 if education else 40 * 0.10
    cert_weight = min(len(certifications) * 40, 100) * 0.10
    
    quality = 0
    if candidate_data.get("name") != "Candidate Profile": quality += 20
    if candidate_data.get("email"): quality += 20
    if candidate_data.get("phone"): quality += 20
    if candidate_data.get("linkedin"): quality += 20
    if candidate_data.get("github"): quality += 20
    quality_weight = quality * 0.05
    
    role_keywords = job_role.lower().split()
    role_match_count = sum(1 for kw in role_keywords if kw in " ".join(skills).lower())
    role_match_score = 90 if role_match_count > 0 else 60
    role_weight = role_match_score * 0.20
    
    overall_baseline = int(skills_weight + projects_weight + exp_weight + edu_weight + cert_weight + quality_weight + role_weight)
    
    return max(10, min(100, overall_baseline)), breakdown

def generate_interview_prep(candidate_data, job_role, experience_level, company="IBM", difficulty="Medium"):
    """
    Orchestrates RAG context retrieval, triggers IBM Granite 4, and performs 
    retry logic to generate a valid JSON prep guide. Reuses responses via caching.
    """
    import time
    skills_query = ", ".join(candidate_data.get("skills", []))
    
    # Check cache first to avoid slow LLM generation
    cache_key = f"prep_{skills_query}_{job_role}_{experience_level}_{company}_{difficulty}"
    cached_report = get_cache(cache_key)
    if cached_report:
        chart_path = cached_report.get("chart_path", "")
        if chart_path and os.path.exists(os.path.join("static", chart_path)):
            cached_report["timings"] = {
                "rag_time": "0.000s (Cache Hit)",
                "llm_time": "0.000s (Cache Hit)"
            }
            return cached_report
            
    # Compute baseline scores locally
    baseline_score, score_breakdown = calculate_weighted_score(candidate_data, job_role, experience_level, company)
    
    # Retrieve contexts from RAG (Optimized: retrieve k=2/1/1 instead of 3/2/2 to reduce tokens by 45%)
    t_rag_start = time.time()
    tech_query = f"{job_role} {experience_level} technical concepts: {skills_query}"
    tech_docs = retrieve_context(tech_query, k=2)
    tech_context = "\n\n".join([doc.page_content for doc in tech_docs])
    
    hr_docs = retrieve_context(f"HR interview question at {company} fit culture", k=1)
    hr_context = "\n\n".join([doc.page_content for doc in hr_docs])
    
    behavioral_docs = retrieve_context(f"Behavioral interview STAR method conflict leadership at {company}", k=1)
    behavioral_context = "\n\n".join([doc.page_content for doc in behavioral_docs])
    rag_time = time.time() - t_rag_start

    # Formulate Prompt
    prompt = f"""You are an elite Technical Recruiter and Career Coach specializing in {company} interview loops.
Generate a comprehensive, highly customized Interview Preparation Guide matching the target settings below.

Target Company: {company} (Tailor behavioral, cultural, and technical styles specifically to this company's hiring standards)
Target Job Role: {job_role}
Difficulty Level: {difficulty} (Generate questions corresponding exactly to this level)
Target Experience Level: {experience_level}

--- CANDIDATE DETAILS ---
- Name: {candidate_data.get("name", "Candidate")}
- Core Skills: {skills_query}
- Education: {"; ".join(candidate_data.get("education", []))}
- Experience Summary: {"; ".join(candidate_data.get("experience", []))}
- Projects: {"; ".join(candidate_data.get("projects", []))}
- Certifications: {"; ".join(candidate_data.get("certifications", []))}
- Achievements: {"; ".join(candidate_data.get("achievements", []))}

--- KNOWLEDGE BASE CONTEXT ---
[TECHNICAL SOURCE DATA]
{tech_context}

[HR SOURCE DATA]
{hr_context}

[BEHAVIORAL SOURCE DATA]
{behavioral_context}

--- EVALUATION BASELINE ---
The baseline calculated match score for this profile is {baseline_score}/100.

--- INSTRUCTIONS ---
You must generate a structured JSON object containing:
1. "overall_score": An integer (0-100) representing their fit, calibrated for {company}'s standards at {difficulty} difficulty.
2. "score_breakdown": An object with ratings (0-100) for categories: "Languages", "Frameworks", "Databases", "AI_ML", "Cloud", "Tools". Use the following defaults: {json.dumps(score_breakdown)} but calibrate them as necessary.
3. "strengths": A list of 3 detailed candidate strengths.
4. "weaknesses": A list of 3 key gaps or development areas.
5. "recommendations": A list of 4 concrete steps to improve their preparation.
6. "technical_questions": 3 questions (appropriate for {difficulty} difficulty) and their model answers.
7. "hr_questions": 2 questions reflecting {company}'s values and their model answers.
8. "behavioral_questions": 2 questions matching the STAR format and their model answers.
9. "tips": A list of 4 specific tips for {company} interviews.
10. "missing_skills": A list of critical skills required for a {job_role} at {company} that this candidate lacks.

You MUST respond with a RAW JSON object matching this schema. Do not output any Markdown boxes, backticks, or extra text.

JSON Schema:
{{
  "overall_score": {baseline_score},
  "score_breakdown": {{
    "Languages": 80,
    "Frameworks": 80,
    "Databases": 80,
    "AI_ML": 80,
    "Cloud": 80,
    "Tools": 80
  }},
  "strengths": [],
  "weaknesses": [],
  "recommendations": [],
  "technical_questions": [
    {{"question": "Q1 text", "answer": "Model Answer 1"}},
    {{"question": "Q2 text", "answer": "Model Answer 2"}},
    {{"question": "Q3 text", "answer": "Model Answer 3"}}
  ],
  "hr_questions": [
    {{"question": "Q1 text", "answer": "Model Answer 1"}},
    {{"question": "Q2 text", "answer": "Model Answer 2"}}
  ],
  "behavioral_questions": [
    {{"question": "Q1 text", "answer": "Model Answer 1"}},
    {{"question": "Q2 text", "answer": "Model Answer 2"}}
  ],
  "tips": [],
  "missing_skills": []
}}

JSON Response:"""

    retries = 3
    parsed_report = None
    raw_response = ""
    t_llm_start = time.time()
    
    for attempt in range(1, retries + 1):
        try:
            logging.info(f"Attempting Granite interview generation. Attempt {attempt} of {retries}...")
            
            current_prompt = prompt
            if attempt > 1:
                current_prompt += f"\n\nWARNING (Attempt {attempt}): Your previous output was not valid JSON. Ensure PURE JSON is returned."
                
            raw_response = generate_response(current_prompt, temperature=0.6, max_tokens=1500)
            
            clean_text = raw_response.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            parsed_report = json.loads(clean_text)
            print("Direct JSON parse succeeded!")
            break
        except Exception as e:
            logging.warning(f"Attempt {attempt} failed to parse: {e}")
            if attempt == retries:
                parsed_report = parse_json_safely(raw_response, baseline_score, score_breakdown)
                
    llm_time = time.time() - t_llm_start
    if not parsed_report:
        parsed_report = get_fallback_report(baseline_score, score_breakdown)
        
    chart_path = generate_skill_breakdown_chart(
        parsed_report.get("score_breakdown", score_breakdown), 
        candidate_data.get("name", "Candidate")
    )
    parsed_report["chart_path"] = chart_path
    
    parsed_report["timings"] = {
        "rag_time": f"{rag_time:.3f}s",
        "llm_time": f"{llm_time:.3f}s"
    }
    
    # Save cache
    set_cache(cache_key, parsed_report)
    return parsed_report

def parse_json_safely(text, baseline_score, score_breakdown):
    """
    Saves state if json fails by extracting tokens using regex.
    """
    try:
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except Exception:
        pass
        
    report = get_fallback_report(baseline_score, score_breakdown)
    score_match = re.search(r'"overall_score"\s*:\s*(\d+)', text)
    if score_match:
        report["overall_score"] = int(score_match.group(1))
        
    tips_matches = re.findall(r'"tips"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    if tips_matches:
        tips_list = re.findall(r'"(.*?)"', tips_matches[0])
        if tips_list:
            report["tips"] = tips_list
            
    return report

def get_fallback_report(baseline_score, score_breakdown):
    return {
        "overall_score": baseline_score,
        "score_breakdown": score_breakdown,
        "strengths": [
            "Good foundational understanding of databases (SQL/NoSQL) and programming languages.",
            "Solid academic projects demonstrating project-based deployment workflows.",
            "Effective use of tools like Git and development frameworks like Flask."
        ],
        "weaknesses": [
            "Lacks formal certifications in target cloud technologies (AWS/Docker).",
            "Limited industrial exposure in high-throughput enterprise systems.",
            "Needs more practice with advanced system design and scaling patterns."
        ],
        "recommendations": [
            "Earn certifications in Cloud Architect or Developer paths (AWS Certified Developer).",
            "Optimize database scripts (indexing, connection pools) in your personal projects.",
            "Study mock system architectures (rate limiters, caches, and load balancers).",
            "Participate in mock coding challenges on algorithmic platforms."
        ],
        "technical_questions": [
            {
                "question": "What is database normalization and how does 3NF differ from BCNF?",
                "answer": "Normalization reduces redundancy. 3NF removes transitive dependencies. BCNF is stronger: for every functional dependency X -> Y, X must be a super key."
            },
            {
                "question": "Explain decorators in Python and when they are executed.",
                "answer": "Decorators modify function behavior. They are executed at import/definition time when the module loads, not at call time."
            },
            {
                "question": "How do processes and threads schedule memory inside operating systems?",
                "answer": "Processes have separate virtual memory spaces. Threads share the heap/code spaces of the parent process but retain distinct stacks."
            }
        ],
        "hr_questions": [
            {
                "question": "Why are you interested in this target company and how do your values align?",
                "answer": "I align with your culture of extreme ownership and transparent peer review, which matches how I build software."
            },
            {
                "question": "Tell me about your career roadmap. Where do you see yourself in 3 years?",
                "answer": "I plan to develop deep competence as an API engineer, taking on scaling problems."
            }
        ],
        "behavioral_questions": [
            {
                "question": "Tell me about a time you resolved a major bug under a tight deadline.",
                "answer": "A memory leak crashed the API 2 hours before submission. I analyzed heap profiles, found unclosed database sessions, wrapped them in context managers, and resolved the leak."
            },
            {
                "question": "Describe a scenario where you convinced a team member to change their technical design.",
                "answer": "My peer wanted to write a manual search regex. I proposed using a FAISS index and set up a quick benchmark showing it was 20x faster."
            }
        ],
        "tips": [
            "Practice writing SQL syntax on whiteboards without IDE autocomplete.",
            "Familiarize yourself with the core cultural leadership guidelines of the company.",
            "Always state metrics in your behavioral STAR results.",
            "Be prepared to draw architecture block diagrams."
        ],
        "missing_skills": ["Docker", "Kubernetes", "Cloud Architectures", "System Design Patterns"]
    }

def generate_jd_match(resume_text, jd_text):
    """
    Compares candidate resume text against a job description text.
    Bypasses LLM call if cached in disk store.
    """
    # Truncate massive inputs to prevent prompt token bloat
    resume_text_trunc = resume_text[:10000]
    jd_text_trunc = jd_text[:10000]
    
    cache_key = f"match_{resume_text_trunc}_{jd_text_trunc}"
    cached_match = get_cache(cache_key)
    if cached_match:
        return cached_match
        
    prompt = f"""You are an AI Talent Acquisition Assistant.
Analyze the candidate's resume text and the provided target Job Description (JD).
Generate a matching report containing the following details:
1. Match Percentage (0-100) based on skills, experience, and role alignment.
2. Missing Skills: Key technical skills or keywords requested in the JD but not found in the resume.
3. Required Technologies: Core technologies mentioned in the JD.
4. Resume Improvement Suggestions: Concrete suggestions to improve the resume for this JD.
5. Learning Roadmap: A step-by-step learning roadmap to bridge key skill gaps.

Resume Text:
{resume_text_trunc}

Job Description Text:
{jd_text_trunc}

You MUST respond ONLY with a raw JSON object matching the following structure. Do not output markdown block wrappers or extra commentary.

JSON Schema:
{{
  "match_percentage": 75,
  "missing_skills": ["Docker", "Kubernetes"],
  "required_technologies": ["Python", "Flask", "PostgreSQL"],
  "improvement_suggestions": [
    "Detail your experience with PostgreSQL query optimizations.",
    "Add certification sections to showcase your AWS credentials."
  ],
  "learning_roadmap": [
    "Week 1: Study Docker container configurations and compose stacks.",
    "Week 2: Deploy mock Flask APIs to Kubernetes clusters."
  ]
}}

JSON Response:"""
    
    retries = 3
    for attempt in range(1, retries + 1):
        try:
            current_prompt = prompt
            if attempt > 1:
                current_prompt += f"\n\nWARNING (Attempt {attempt}): Your previous output was not valid JSON. Ensure PURE JSON is returned."
            
            raw = generate_response(current_prompt, temperature=0.5, max_tokens=1000)
            clean = raw.strip()
            if clean.startswith("```json"): clean = clean[7:]
            elif clean.startswith("```"): clean = clean[3:]
            if clean.endswith("```"): clean = clean[:-3]
            clean = clean.strip()
            
            result = json.loads(clean)
            set_cache(cache_key, result)
            return result
        except Exception as e:
            logging.warning(f"JD Match attempt {attempt} failed: {e}")
            if attempt == retries:
                fallback = {
                    "match_percentage": 70,
                    "missing_skills": ["Docker", "AWS Services", "API Testing"],
                    "required_technologies": ["Python", "SQL", "Flask"],
                    "improvement_suggestions": [
                        "Include metrics like 'improved speed by X%' in your experience descriptions.",
                        "Add details regarding API design, unit testing frameworks, and databases."
                    ],
                    "learning_roadmap": [
                        "Stage 1: Practice writing mock SQL queries (Window functions and subqueries).",
                        "Stage 2: Containerize your Flask applications using Docker.",
                        "Stage 3: Learn basic CI/CD pipeline structures using GitHub Actions."
                    ]
                }
                set_cache(cache_key, fallback)
                return fallback

def generate_mock_interview_questions(candidate_skills, job_role, company, difficulty):
    """
    Generates 5 tailored mock interview questions. Uses cache.
    """
    cache_key = f"mock_qs_{candidate_skills}_{job_role}_{company}_{difficulty}"
    cached_qs = get_cache(cache_key)
    if cached_qs:
        return cached_qs
        
    prompt = f"""You are an AI Interviewer at {company}.
Based on the candidate skills below, generate exactly 5 interview questions for a {difficulty} level {job_role} interview.
Make the questions relevant to {company}'s technical standards.

Candidate Skills: {candidate_skills}

You MUST respond ONLY with a raw JSON array containing exactly 5 string elements. Do not include markdown box markers.

JSON Schema:
[
  "Question 1 text",
  "Question 2 text",
  "Question 3 text",
  "Question 4 text",
  "Question 5 text"
]

JSON Response:"""

    retries = 3
    for attempt in range(1, retries + 1):
        try:
            raw = generate_response(prompt, temperature=0.7, max_tokens=600)
            clean = raw.strip()
            if clean.startswith("```json"): clean = clean[7:]
            elif clean.startswith("```"): clean = clean[3:]
            if clean.endswith("```"): clean = clean[:-3]
            clean = clean.strip()
            
            questions = json.loads(clean)
            if isinstance(questions, list) and len(questions) >= 5:
                res = questions[:5]
                set_cache(cache_key, res)
                return res
        except Exception as e:
            logging.warning(f"Mock Question generation attempt {attempt} failed: {e}")
            if attempt == retries:
                fallback = [
                    f"Explain decorators in Python and how they are useful in a {job_role} role.",
                    f"How do you optimize a slow-running SQL query that uses multiple joins?",
                    f"What is the difference between a process and a thread, and how does that affect concurrency?",
                    f"Describe a challenging technical project you built. What architectural choices did you make?",
                    f"Why do you want to work at {company} and how does this role fit your career roadmap?"
                ]
                set_cache(cache_key, fallback)
                return fallback

def evaluate_mock_answer(question, user_answer, job_role, company, difficulty):
    """
    Evaluates a candidate's answer to a mock interview question. Uses cache.
    """
    user_answer_trunc = user_answer[:4000]
    cache_key = f"mock_eval_{question}_{user_answer_trunc}_{job_role}_{company}_{difficulty}"
    cached_eval = get_cache(cache_key)
    if cached_eval:
        return cached_eval
        
    prompt = f"""You are an AI Interviewer at {company}.
Evaluate the candidate's answer for the following {difficulty} level {job_role} interview question.

Question:
{question}

Candidate Answer:
{user_answer_trunc}

Provide:
1. A numerical rating score (0-100) for their answer.
2. Strengths in their answer.
3. Weaknesses or missing details in their answer.
4. Corrective feedback.
5. An ideal model answer they could have given.

You MUST respond ONLY with a raw JSON object matching the following structure:
{{
  "score": 80,
  "strengths": "Clearly explains core concepts with accurate examples.",
  "weaknesses": "Missed discussing indexing optimization impacts.",
  "feedback": "Try incorporating system performance metrics and concrete database details.",
  "ideal_answer": "An ideal answer would cover..."
}}

JSON Response:"""

    retries = 3
    for attempt in range(1, retries + 1):
        try:
            raw = generate_response(prompt, temperature=0.5, max_tokens=800)
            clean = raw.strip()
            if clean.startswith("```json"): clean = clean[7:]
            elif clean.startswith("```"): clean = clean[3:]
            if clean.endswith("```"): clean = clean[:-3]
            clean = clean.strip()
            
            result = json.loads(clean)
            set_cache(cache_key, result)
            return result
        except Exception as e:
            logging.warning(f"Answer evaluation attempt {attempt} failed: {e}")
            if attempt == retries:
                fallback = {
                    "score": 75,
                    "strengths": "Answer provides a good basic overview of the topic.",
                    "weaknesses": "Lacks specific technical depth and metrics.",
                    "feedback": "Incorporate details about implementation context and potential bottlenecks.",
                    "ideal_answer": f"For a {job_role} role at {company}, a strong answer would describe the concept clearly, detail actual projects where you applied it, and mention performance trade-offs."
                }
                set_cache(cache_key, fallback)
                return fallback


# ===========================================================================
# STAR METHOD EVALUATOR (Phase 2.1)
# ===========================================================================
def evaluate_star_answer(question: str, user_answer: str, job_role: str, company: str) -> dict:
    """
    Evaluates a behavioural answer against the STAR framework.

    Returns a dict with:
        star_score        (int, 0-100)
        situation_score   (int)
        task_score        (int)
        action_score      (int)
        result_score      (int)
        missing_components (list[str])
        suggestions        (list[str])
        improved_example   (str)
        star_breakdown     (dict)
    """
    user_answer_trunc = user_answer[:4000]
    cache_key = f"star_{question[:80]}_{user_answer_trunc[:80]}_{job_role}_{company}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    prompt = f"""You are an expert interview coach specialising in behavioural assessment.
Evaluate the following behavioural answer against the STAR method framework.

Role: {job_role} at {company}
Question: {question}
Candidate Answer: {user_answer_trunc}

Evaluate each STAR component on a scale of 0-25:
- Situation (0-25): Was a clear context provided? (2-3 sentences expected)
- Task (0-25): Was the candidate's responsibility/challenge clear?
- Action (0-25): Did they describe specific personal actions taken? (this is the core, 50-60%)
- Result (0-25): Were quantified outcomes or learnings mentioned?

You MUST respond ONLY with a raw JSON object in this exact schema:
{{
  "star_score": 75,
  "situation_score": 18,
  "task_score": 20,
  "action_score": 22,
  "result_score": 15,
  "missing_components": ["Result lacks quantified metrics"],
  "suggestions": [
    "Add a specific number to your result (e.g. 'reduced time by 30%')",
    "Make your Action section more detailed — describe the exact steps you personally took"
  ],
  "improved_example": "A strong STAR answer for this question would begin: 'In my previous role at X... (Situation). My task was to... (Task). I specifically took these actions: ... (Action). As a result, we achieved... (Result with metric).'"
}}

JSON Response:"""

    retries = 3
    for attempt in range(1, retries + 1):
        try:
            raw = generate_response(prompt, temperature=0.5, max_tokens=800)
            clean = raw.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            elif clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            result = json.loads(clean.strip())
            set_cache(cache_key, result)
            return result
        except Exception as e:
            logging.warning(f"STAR evaluation attempt {attempt} failed: {e}")
            if attempt == retries:
                fallback = {
                    "star_score": 65,
                    "situation_score": 15,
                    "task_score": 18,
                    "action_score": 20,
                    "result_score": 12,
                    "missing_components": ["Result lacks quantified outcomes"],
                    "suggestions": [
                        "Quantify your Result component with numbers, percentages, or timeframes.",
                        "Expand your Action section — it should be 50-60% of your answer.",
                        "Start with a crisp one-sentence Situation to set context quickly.",
                    ],
                    "improved_example": (
                        f"For a {job_role} role, a strong STAR answer would include: "
                        "'In my previous project (Situation), I was responsible for... (Task). "
                        "I specifically took the following steps: ... (Action). "
                        "As a result, we achieved X% improvement / delivered on time / resolved the issue. (Result)'"
                    ),
                }
                set_cache(cache_key, fallback)
                return fallback


# ===========================================================================
# ADAPTIVE DIFFICULTY ENGINE (Phase 1.4)
# ===========================================================================
DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"]


def compute_adaptive_difficulty(current_difficulty: str, recent_scores: list) -> str:
    """
    Adjust the interview difficulty based on recent answer scores.

    Rules:
    - If the last 2 answers average >= 80: increase difficulty
    - If the last 2 answers average <= 50: decrease difficulty
    - Otherwise: maintain current level

    Parameters
    ----------
    current_difficulty : str
        Current difficulty level ("Easy", "Medium", "Hard").
    recent_scores : list[int]
        List of scores for the most recently submitted answers.

    Returns
    -------
    str
        New difficulty level.
    """
    if len(recent_scores) < 2:
        return current_difficulty

    last_two = [s for s in recent_scores if isinstance(s, (int, float))][-2:]
    if not last_two:
        return current_difficulty

    avg = sum(last_two) / len(last_two)
    idx = DIFFICULTY_LEVELS.index(current_difficulty) if current_difficulty in DIFFICULTY_LEVELS else 1

    if avg >= 80 and idx < len(DIFFICULTY_LEVELS) - 1:
        new = DIFFICULTY_LEVELS[idx + 1]
        logging.info(f"Adaptive difficulty: escalating from {current_difficulty} to {new} (avg={avg:.0f})")
        return new
    elif avg <= 50 and idx > 0:
        new = DIFFICULTY_LEVELS[idx - 1]
        logging.info(f"Adaptive difficulty: reducing from {current_difficulty} to {new} (avg={avg:.0f})")
        return new

    return current_difficulty


def generate_adaptive_question(
    candidate_skills: str,
    job_role: str,
    company: str,
    difficulty: str,
    previous_questions: list,
    question_type: str = "technical",
) -> str:
    """
    Generate a single adaptive follow-up question based on current difficulty,
    question type, and previously asked questions (to avoid repetition).
    """
    prev_str = "\n".join(f"- {q}" for q in previous_questions[-3:]) if previous_questions else "None"
    company_profile = COMPANY_PROFILES.get(company, DEFAULT_COMPANY_PROFILE)

    prompt = f"""You are an AI interviewer at {company}.
Generate exactly ONE {difficulty} difficulty {question_type} interview question for a {job_role} candidate.

Company Focus: {company_profile['focus']}
Candidate Skills: {candidate_skills}

Previously Asked Questions (DO NOT repeat these):
{prev_str}

Respond with ONLY the question text — no numbering, no explanation, no JSON.
Question:"""

    try:
        raw = generate_response(prompt, temperature=0.7, max_tokens=200)
        question = raw.strip().strip('"').strip("'").strip()
        # Remove any leading "Q:" or "Question:" prefix
        question = re.sub(r"^(Q\d*[:.]?\s*|Question\s*\d*[:.]?\s*)", "", question, flags=re.IGNORECASE)
        return question if question else f"Explain a challenging {job_role} problem you solved recently."
    except Exception as e:
        logging.warning(f"Adaptive question generation failed: {e}")
        return f"Describe a situation where you demonstrated {job_role} skills effectively."


# ===========================================================================
# BEHAVIOURAL INTERVIEW MODULE (Phase 2.3)
# ===========================================================================
def generate_behavioural_questions(
    candidate_data: dict,
    company: str,
    competencies: list | None = None,
) -> list:
    """
    Generate 7 behavioural questions covering key competency areas,
    tailored to the company culture.

    Parameters
    ----------
    candidate_data : dict
        Parsed resume data.
    company : str
        Target company name.
    competencies : list[str], optional
        Competency areas to cover. Defaults to all 7 categories.

    Returns
    -------
    list[dict] — each item has: competency, question
    """
    if competencies is None:
        competencies = BEHAVIOURAL_COMPETENCIES

    cache_key = f"behavioural_{company}_{','.join(competencies)}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    company_profile = COMPANY_PROFILES.get(company, DEFAULT_COMPANY_PROFILE)
    comp_list = "\n".join(f"- {c}" for c in competencies)

    prompt = f"""You are an expert behavioural interviewer at {company}.
Generate exactly one STAR-format behavioural interview question for each of these competency areas:

{comp_list}

Company Values: {company_profile['values']}
Interview Style: {company_profile['style']}

Each question must:
1. Start with "Tell me about a time when..." or "Describe a situation where..."
2. Be specific to the competency area
3. Be aligned with {company}'s culture

Respond ONLY with a raw JSON array:
[
  {{"competency": "Leadership", "question": "Tell me about a time you..."}},
  {{"competency": "Teamwork", "question": "Describe a situation where..."}}
]

JSON Response:"""

    retries = 3
    for attempt in range(1, retries + 1):
        try:
            raw = generate_response(prompt, temperature=0.7, max_tokens=800)
            clean = raw.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            elif clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            result = json.loads(clean.strip())
            if isinstance(result, list) and len(result) >= len(competencies) - 1:
                set_cache(cache_key, result)
                return result
        except Exception as e:
            logging.warning(f"Behavioural question generation attempt {attempt} failed: {e}")

    # Fallback
    fallback = [
        {"competency": "Leadership", "question": "Tell me about a time you led a team through a challenging technical project."},
        {"competency": "Teamwork", "question": "Describe a situation where you had to collaborate across teams to deliver a result."},
        {"competency": "Communication", "question": "Tell me about a time you had to explain a complex technical concept to a non-technical stakeholder."},
        {"competency": "Conflict Resolution", "question": "Describe a situation where you disagreed with a colleague. How did you resolve it?"},
        {"competency": "Time Management", "question": "Tell me about a time you had to manage multiple competing priorities under a tight deadline."},
        {"competency": "Problem Solving", "question": "Describe the most complex technical problem you've encountered and how you solved it."},
        {"competency": "Adaptability", "question": "Tell me about a time you had to quickly learn a new technology or change direction mid-project."},
    ]
    set_cache(cache_key, fallback)
    return fallback


def evaluate_behavioural_answer(
    competency: str,
    question: str,
    user_answer: str,
    company: str,
) -> dict:
    """
    Evaluate a behavioural answer combining STAR scoring and
    competency-specific assessment.
    """
    # Re-use STAR evaluator and enrich with competency context
    star_result = evaluate_star_answer(question, user_answer, competency, company)

    # Add competency-specific feedback
    star_result["competency"] = competency
    star_result.setdefault("suggestions", [])
    if competency == "Leadership" and star_result.get("star_score", 0) < 70:
        star_result["suggestions"].append(
            f"For {company}, emphasise how you influenced outcomes without formal authority."
        )
    elif competency == "Conflict Resolution" and star_result.get("star_score", 0) < 70:
        star_result["suggestions"].append(
            "Focus on data-driven resolution — show you used evidence rather than opinion."
        )

    return star_result


# ===========================================================================
# PERSONALIZED LEARNING PLAN (Phase 3.3)
# ===========================================================================
def generate_learning_plan(
    candidate_data: dict,
    job_role: str,
    company: str,
    missing_skills: list,
    weak_categories: list,
) -> dict:
    """
    Generate a personalised daily/weekly learning plan.

    Returns
    -------
    dict with keys:
        daily_goals       (list[str])
        weekly_milestones (list[str])
        priority_topics   (list[str])
        estimated_weeks   (int)
        resources         (list[dict] with name, type, duration)
    """
    cache_key = f"plan_{job_role}_{company}_{'_'.join(sorted(missing_skills[:5]))}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    company_profile = COMPANY_PROFILES.get(company, DEFAULT_COMPANY_PROFILE)
    missing_str = ", ".join(missing_skills[:8]) if missing_skills else "None identified"
    weak_str = ", ".join(weak_categories[:5]) if weak_categories else "None"

    prompt = f"""You are a career coach creating a personalised interview preparation plan.

Target Role: {job_role}
Target Company: {company}
Missing Skills: {missing_str}
Weak Categories: {weak_str}
Company Focus: {company_profile['focus']}

Generate a structured preparation plan with:
1. 3 daily practice goals (specific, actionable, 30-60 min each)
2. 4 weekly milestones over 4 weeks
3. 5 priority topics to study immediately
4. 3-5 recommended learning resources with estimated time

You MUST respond ONLY with a raw JSON object:
{{
  "daily_goals": [
    "Solve 1 LeetCode medium problem focusing on arrays or trees",
    "Review and rewrite 2 resume bullet points with quantified metrics",
    "Answer 1 mock behavioural question using the STAR method"
  ],
  "weekly_milestones": [
    "Week 1: Complete foundational review of {job_role} core concepts",
    "Week 2: Build and deploy a small project using a missing skill",
    "Week 3: Complete 3 full mock interviews with self-evaluation",
    "Week 4: Final polish — resume review, portfolio update, company research"
  ],
  "priority_topics": ["Topic 1", "Topic 2", "Topic 3", "Topic 4", "Topic 5"],
  "estimated_weeks": 4,
  "resources": [
    {{"name": "Resource name", "type": "Course/Book/Platform", "duration": "X hours"}},
    {{"name": "Resource name", "type": "Practice Platform", "duration": "Ongoing"}}
  ]
}}

JSON Response:"""

    retries = 3
    for attempt in range(1, retries + 1):
        try:
            raw = generate_response(prompt, temperature=0.6, max_tokens=900)
            clean = raw.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            elif clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            result = json.loads(clean.strip())
            set_cache(cache_key, result)
            return result
        except Exception as e:
            logging.warning(f"Learning plan generation attempt {attempt} failed: {e}")

    # Fallback
    fallback = {
        "daily_goals": [
            f"Solve 1 coding problem related to {job_role} core concepts (30 min).",
            "Review and improve 2 resume bullet points with quantified results (20 min).",
            "Practice 1 STAR behavioural answer for a common competency (20 min).",
        ],
        "weekly_milestones": [
            f"Week 1: Master the foundational technical concepts for {job_role}.",
            f"Week 2: Build a mini project using {', '.join(missing_skills[:2]) if missing_skills else 'key missing skills'}.",
            "Week 3: Complete 3 mock interviews and analyse your weak areas.",
            "Week 4: Final review — resume, GitHub portfolio, and company research.",
        ],
        "priority_topics": missing_skills[:5] if missing_skills else [
            "System Design fundamentals",
            "Data Structures & Algorithms",
            "SQL and database optimisation",
            "RESTful API design patterns",
            "Docker and containerisation",
        ],
        "estimated_weeks": 4,
        "resources": [
            {"name": "LeetCode", "type": "Practice Platform", "duration": "Daily — 30 min"},
            {"name": "IBM SkillsBuild", "type": "Free Course Platform", "duration": "5-10 hours"},
            {"name": "System Design Primer (GitHub)", "type": "Free Resource", "duration": "8-10 hours"},
            {"name": "Cracking the Coding Interview", "type": "Book", "duration": "20+ hours"},
            {"name": "HackerRank Interview Preparation Kit", "type": "Practice Platform", "duration": "Ongoing"},
        ],
    }
    set_cache(cache_key, fallback)
    return fallback
