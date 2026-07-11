# AI Interview Coach Agent

AI Interview Coach Agent is an intelligent interview preparation platform developed as part of the **IBM SkillsBuild** and **Edunet Foundation University Engagement Program**. The application leverages **IBM watsonx.ai**, **IBM Granite Foundation Models**, **Retrieval-Augmented Generation (RAG)**, and **FAISS Vector Database** to provide ATS resume analysis, career matching, AI-powered mock interviews, interview performance evaluation, and personalized learning recommendations.

---

## Live Application

**Live Demo**

https://interviewtraineragent-174815016344.asia-south1.run.app/

**Model**

IBM Granite 4 H Small

**Deployment Platform**

Google Cloud Run

---

## Project Overview

The platform assists students and job seekers in preparing for technical interviews by analyzing resumes, comparing them with job descriptions, identifying missing skills, conducting AI-powered mock interviews, and generating detailed feedback reports.

The application integrates IBM Granite Foundation Models through IBM watsonx.ai to generate personalized interview questions, evaluate responses, and recommend improvement strategies.

---

## Features

| Module | Description |
|---------|-------------|
| Resume Parser | Extracts candidate information from resumes |
| ATS Analysis | Calculates ATS score and identifies missing keywords |
| Career Match | Matches resumes with job descriptions |
| Skill Gap Analysis | Identifies missing technical skills |
| AI Mock Interview | Conducts company-specific mock interviews |
| Performance Evaluation | Evaluates interview answers using IBM Granite |
| Learning Roadmap | Generates personalized learning recommendations |
| Analytics Dashboard | Displays interview statistics and visual reports |
| PDF Report | Generates downloadable interview reports |
| Knowledge Base | Uses RAG with FAISS for contextual responses |

---

## Technology Stack

| Category | Technologies |
|----------|--------------|
| Artificial Intelligence | IBM watsonx.ai, IBM Granite 4 H Small |
| Backend | Flask, Python |
| Frontend | HTML, CSS, JavaScript |
| Vector Database | FAISS |
| AI Technique | Retrieval-Augmented Generation (RAG) |
| Visualization | Matplotlib |
| PDF Generation | PyMuPDF |
| Deployment | Docker, Google Cloud Run |

---

## System Architecture

```text
                 User
                   │
                   ▼
         Flask Web Application
                   │
         Resume Processing Layer
                   │
      ┌────────────┴────────────┐
      │                         │
      ▼                         ▼
 Resume Parser           Knowledge Base
      │                         │
      └────────────┬────────────┘
                   ▼
          FAISS Vector Database
                   │
                   ▼
      IBM watsonx.ai (Granite Model)
                   │
      ┌────────────┼────────────┐
      ▼            ▼            ▼
 ATS Analysis  Mock Interview  Career Match
      │            │            │
      └────────────┼────────────┘
                   ▼
       Dashboard & PDF Report
```

---

## Application Workflow

```text
Upload Resume
      │
      ▼
Resume Parsing
      │
      ▼
ATS Analysis
      │
      ▼
Career Match Analysis
      │
      ▼
Skill Gap Analysis
      │
      ▼
Mock Interview
      │
      ▼
Performance Evaluation
      │
      ▼
Learning Roadmap
      │
      ▼
PDF Report Generation
```

---

## Project Structure

```text
InterviewTrainerAgent/
│
├── app.py
├── granite.py
├── interview.py
├── rag.py
├── analytics.py
├── ats_analyzer.py
├── skill_gap.py
├── readiness_score.py
├── resume_parser.py
├── pdf_generator.py
├── requirements.txt
├── Dockerfile
├── app.json
├── README.md
│
├── knowledge_base/
├── screenshots/
├── static/
├── templates/
├── uploads/
└── vector_db/
```

---

## Installation

Clone the repository.

```bash
git clone https://github.com/sisirats005-ux/InterviewTrainerAgent.git

cd InterviewTrainerAgent
```

Create a virtual environment.

```bash
python -m venv .venv
```

Windows

```bash
.venv\Scripts\activate
```

Linux/macOS

```bash
source .venv/bin/activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Create a `.env` file.

```env
WATSONX_APIKEY=your_api_key
WATSONX_PROJECT_ID=your_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
FLASK_SECRET_KEY=your_secret_key
```

Run the application.

```bash
python app.py
```

---

## Deployment

The application is containerized using Docker and deployed on **Google Cloud Run**.

Required environment variables:

- WATSONX_APIKEY
- WATSONX_PROJECT_ID
- WATSONX_URL
- FLASK_SECRET_KEY

---

## Future Enhancements

- Voice-based interview mode
- Webcam-based interview analysis
- Coding interview assessment
- Multi-language interview support
- Mobile application

---

## License

This project is licensed under the MIT License.

---

