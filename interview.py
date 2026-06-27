import json
import re
import os
import logging
import hashlib
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
