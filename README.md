# Interview Trainer Agent (Upgraded)

An advanced, production-ready AI interview preparation and profile matching dashboard built for the **IBM SkillsBuild + Edunet Foundation** initiative.

This application uses a Retrieval-Augmented Generation (RAG) architecture powered by **IBM watsonx.ai Granite 4** (`ibm/granite-4-h-small`) and a local **FAISS** vector database. It parses resumes and job descriptions, scores candidacy alignment against companies (such as IBM, Google, or Microsoft) and difficulty levels, and guides applicants through interactive mock interviews.

---

## Key Features

- **Advanced Resume Parsing**: Extracts Name, Email, Phone, LinkedIn, GitHub, Skills, Education, Experience, Projects, Certifications, and Achievements using **PyMuPDF**. Technical skills are classified into Languages, Frameworks, Databases, AI/ML, Cloud, and Tools.
- **Job Description Matcher**: Compares candidate resumes against job descriptions (PDF, DOCX, or TXT) to calculate Match Percentages, extract missing technologies, and generate custom upskilling roadmaps.
- **Weighted Readiness Scoring**: Replaces raw percentages with a structured score model weighting skills (25%), role fit (20%), experience (15%), projects (15%), certifications (10%), education (10%), and resume layout quality (5%).
- **Matplotlib Visual Analytics**: Compiles category alignment ratings into horizontal bar charts saved in `static/charts/` and rendered on the results dashboard.
- **Company & Difficulty Profiles**: Adjusts Granite prompts based on selected companies (e.g. Google's algorithmic focus vs IBM's enterprise hybrid cloud focus) and difficulty levels (Easy, Medium, Hard).
- **Interactive Mock Interview Session**: Guides candidates through a 5-question mock loop, maintaining state in Flask sessions. It evaluates text answers for scores (0-100), strengths, weaknesses, corrective feedback, and ideal answers.
- **Multi-Format RAG Cache**: Splits and indexes PDF, DOCX, TXT, and Markdown files in `knowledge_base/`. Tracks changes using `vector_db/manifest.json` to automatically rebuild the FAISS database index only when files change.
- **Robust JSON Parsing & Retries**: Specifies strict JSON formats from Granite and runs a validation loop (up to 3 retries) with warning logs, falling back to a regex decoder to prevent application exceptions.
- **PDF Report Downloads**: Compiles complete interview manuals (with scores, Q&As, and roadmaps) into multi-page PDFs using PyMuPDF.
- **Production Security & Logs**: Restricts uploads to 4MB, checks file headers for magic bytes (`%PDF-` / `PK`) to verify MIME signatures, writes execution trails to `app.log`, and serves errors gracefully.

---

## Upgraded File Structure

```
InterviewTrainerAgent/
│
├── .env                  # Local credentials
├── .env.example          # Environment variables template
├── .gitignore            # Excludes credentials, caches, and logs
├── app.py                # Flask server, route maps, uploads, session managers
├── granite.py            # IBM watsonx.ai LLM wrapper
├── rag.py                # Multi-format document loader & auto-rebuild RAG pipeline
├── resume_parser.py      # PDF parsing, categorized skills list, and detail extractor
├── interview.py          # Prompt engineering, matching, and JSON retry loops
├── pdf_generator.py      # PyMuPDF-based multi-page PDF manual compiler
├── run_tests.py          # Unified unittest suite (parser, LLM, RAG, scoring, routes)
├── requirements.txt      # Python dependencies
├── Dockerfile            # Container build spec
├── docker-compose.yml    # Multi-container orchestration spec
├── render.yaml           # Render deployment configuration spec
├── Procfile              # Gunicorn web task spec
│
├── knowledge_base/       # Source files for RAG index
├── static/               # CSS, JS, and Matplotlib charts
├── templates/            # HTML views (home, result, mock interview, JD match, error)
├── uploads/              # Temp upload storage
└── vector_db/            # Cached FAISS files and manifest.json
```

---

## Setup & Running Locally

### 1. Initialize Virtual Environment
Initialize and activate a virtual environment in the project root:
```bash
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux/MacOS:
source .venv/bin/activate
```

### 2. Install Requirements
```bash
pip install -r requirements.txt
```

### 3. Configure Credentials (`.env`)
Create a `.env` file containing your watsonx configurations:
```env
WATSONX_APIKEY=your_watsonx_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
WATSONX_URL=https://eu-de.ml.cloud.ibm.com
FLASK_SECRET_KEY=some_random_secret_key_string
```

### 4. Compile Sample PDF Resume
Create the default test profile `sample_resume.pdf` (contains skills, contact info, CKA & AWS certifications, and university achievements):
```bash
python generate_sample_resume.py
```

### 5. Run Automated Tests
Execute the testing suite to verify that all modules are integrated:
```bash
python run_tests.py
```
You should see: `Ran 5 tests ... OK`.

### 6. Start local development server
```bash
python app.py
```
Navigate to `http://127.0.0.1:5000/` in your browser.

---

## Deployment Instructions

### A. Deploy to Render
Render automatically discovers and loads configuration details from `render.yaml`.
1. Push your project to a GitHub repository.
2. Log into the [Render Dashboard](https://dashboard.render.com/).
3. Click **New** -> **Blueprints**.
4. Connect your GitHub repository. Render will automatically configure the Python environment, install Gunicorn, set up the build command (`pip install -r requirements.txt`), and launch the start command (`gunicorn app:app`).
5. Open **Environment Variables** in Render, and input your `WATSONX_APIKEY` and `WATSONX_PROJECT_ID` secret keys.

### B. Deploy to IBM Code Engine
IBM Code Engine is a fully managed serverless platform that runs containerized workloads.
1. Build the Docker image locally or using Docker Hub:
   ```bash
   docker build -t your-dockerhub-username/interview-trainer-agent:latest .
   docker push your-dockerhub-username/interview-trainer-agent:latest
   ```
2. Log into the IBM Cloud Console and navigate to **Code Engine**.
3. Create a **Project** in Code Engine.
4. Go to **Applications** -> Click **Create**.
5. Configure the Application:
   - **Name**: `interview-trainer-agent`
   - **Image reference**: `docker.io/your-dockerhub-username/interview-trainer-agent:latest`
   - **Target Port**: `5000`
6. Add the following **Environment Variables**:
   - `WATSONX_APIKEY` (Use Code Engine secret reference for security)
   - `WATSONX_PROJECT_ID` (Define as a Literal value)
   - `WATSONX_URL` (Set to `https://eu-de.ml.cloud.ibm.com`)
   - `FLASK_SECRET_KEY` (Define as a secure secret)
7. Click **Create** to deploy. Code Engine will build the container, route traffic, and scale instances to zero when idle.
