import os
import json
import logging
import uuid
import time
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename
from resume_parser import parse_resume, extract_text
from interview import generate_interview_prep, generate_jd_match, generate_mock_interview_questions, evaluate_mock_answer
from rag import build_vector_db
from pdf_generator import generate_pdf_report

# Configure Gunicorn-ready logging to app.log and stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("InterviewTrainer")

app = Flask(__name__)

# Flask Session & Directory Configurations
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev_secret_key_carbon_998877")
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads"))
ALLOWED_EXTENSIONS = {"pdf", "txt", "docx"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # Enforce strict 4MB upload limit

# Ensure runtime directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("vector_db", exist_ok=True)

# Build FAISS RAG index on startup (only in child worker process under Flask reloader)
if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    logger.info("Initializing FAISS knowledge base index checker on application startup...")
    try:
        build_vector_db()
        logger.info("FAISS vector database check complete.")
    except Exception as e:
        logger.error(f"Failed to build vector database on startup: {e}", exc_info=True)

# ====================================================
# FILESYSTEM-BASED SESSION CACHING (PREVENT LARGE COOKIES)
# ====================================================
def save_session_data(report_id, data):
    """
    Saves heavy data attributes directly to disk cache.
    """
    if not report_id:
        return
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], f"session_{report_id}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save session data to disk: {e}")

def load_session_data(report_id):
    """
    Loads session details from local disk cache.
    """
    if not report_id:
        return {}
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], f"session_{report_id}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load session data from disk: {e}")
    return {}

def cleanup_old_sessions():
    """
    Garbage collector that deletes cached files older than 2 hours.
    """
    try:
        now = time.time()
        for filename in os.listdir(app.config["UPLOAD_FOLDER"]):
            if filename.startswith("session_") and filename.endswith(".json"):
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                if os.path.getmtime(file_path) < now - 2 * 3600:
                    os.remove(file_path)
                    logger.info(f"Cleaned up expired session file: {filename}")
    except Exception as e:
        logger.error(f"Error cleaning up old session files: {e}")

def verify_file_mime_signature(file_stream, expected_format):
    """
    Performs production-grade security signature checking on uploaded bytes.
    - PDF must start with %PDF- (50 44 46 2D)
    - DOCX (OpenXML zip) must start with PK (50 4B)
    - TXT files are checked for standard decode compatibility
    """
    file_stream.seek(0)
    header = file_stream.read(4)
    file_stream.seek(0) # Reset stream pointer
    
    if expected_format == "pdf":
        return header.startswith(b"%PDF")
    elif expected_format == "docx":
        return header.startswith(b"PK")
    elif expected_format == "txt":
        try:
            header.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    return False

@app.route("/", methods=["GET", "POST"])
def home():
    """
    Handles landing page (GET) and processes the form submission (POST)
    for generating the main Interview Trainer guide.
    """
    watsonx_configured = bool(os.getenv("WATSONX_APIKEY") and os.getenv("WATSONX_PROJECT_ID"))

    if request.method == "POST":
        if not watsonx_configured:
            logger.warning("Submission blocked: watsonx.ai credentials missing in env.")
            flash("watsonx.ai credentials are not configured in your .env file.", "warning")
            return redirect(url_for("home"))
            
        # Parameter validation
        if "resume" not in request.files:
            flash("No resume file found in upload request.", "danger")
            return redirect(url_for("home"))
            
        file = request.files["resume"]
        job_role = request.form.get("job_role", "").strip()
        experience_level = request.form.get("experience_level", "").strip()
        company = request.form.get("company", "IBM").strip()
        difficulty = request.form.get("difficulty", "Medium").strip()
        
        if file.filename == "":
            flash("No resume file selected.", "danger")
            return redirect(url_for("home"))
            
        if not job_role or not experience_level:
            flash("Please complete target job role and experience selections.", "danger")
            return redirect(url_for("home"))

        # Verify extension and file headers
        filename = secure_filename(file.filename)
        _, ext = os.path.splitext(filename.lower())
        ext = ext.lstrip(".")
        
        if ext != "pdf" or not verify_file_mime_signature(file, "pdf"):
            logger.warning(f"Upload blocked: file '{filename}' failed security signature check.")
            flash("Security check failed: Only valid PDF resume uploads are supported.", "danger")
            return redirect(url_for("home"))

        try:
            # Save file securely
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            logger.info(f"Resume uploaded successfully: {filename}")
            
            # Track Resume Parsing Time
            t_start = time.time()
            t_parse_start = time.time()
            candidate_data = parse_resume(file_path)
            parse_time = time.time() - t_parse_start
            
            if not candidate_data["skills"] and not candidate_data["raw_text"]:
                flash("Failed to parse text. Please ensure the PDF is not encrypted or blank.", "danger")
                return redirect(url_for("home"))
                
            # Track RAG + Granite Generation Time
            logger.info(f"Generating prep guide for {candidate_data['name']} (Role: {job_role}, Company: {company})")
            t_gen_start = time.time()
            report = generate_interview_prep(candidate_data, job_role, experience_level, company, difficulty)
            gen_time = time.time() - t_gen_start
            total_time = time.time() - t_start
            
            # Extract internal RAG and LLM breakdown times
            timings = report.get("timings", {})
            rag_time_str = timings.get("rag_time", "0.000s")
            llm_time_str = timings.get("llm_time", "0.000s")
            
            # Print developer performance logs in debug mode
            logger.info(f"--- Developer Performance Metrics ---")
            logger.info(f"Resume Parsing Time: {parse_time:.4f}s")
            logger.info(f"RAG Retrieval Time: {rag_time_str}")
            logger.info(f"Granite API Response Time: {llm_time_str}")
            logger.info(f"Total Request Execution Time: {total_time:.4f}s")
            
            metrics = {
                "parse_time": f"{parse_time:.3f}s",
                "rag_time": rag_time_str,
                "llm_time": llm_time_str,
                "total_time": f"{total_time:.3f}s"
            }
            
            # Save relevant profile data in disk cache rather than Flask session
            report_id = str(uuid.uuid4())
            session_data = {
                "report": report,
                "candidate": candidate_data,
                "job_role": job_role,
                "experience_level": experience_level,
                "company": company,
                "difficulty": difficulty,
                "metrics": metrics
            }
            save_session_data(report_id, session_data)
            cleanup_old_sessions()
            
            # Store only metadata and session index ID in browser cookie
            session["report_id"] = report_id
            session["current_job_role"] = job_role
            session["current_experience_level"] = experience_level
            session["current_company"] = company
            session["current_difficulty"] = difficulty
            
            # Clean up upload
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return render_template(
                "result.html",
                report=report,
                candidate=candidate_data,
                job_role=job_role,
                experience_level=experience_level,
                company=company,
                difficulty=difficulty,
                metrics=metrics
            )
        except Exception as ex:
            logger.error(f"Error serving interview generation route: {ex}", exc_info=True)
            flash(f"Generation failed: {ex}", "danger")
            return redirect(url_for("home"))

    return render_template("index.html", watsonx_configured=watsonx_configured)

# ====================================================
# JOB DESCRIPTION MATCHER MODULE (PHASE 6)
# ====================================================
@app.route("/jd_match", methods=["GET", "POST"])
def jd_match():
    """
    Renders double-upload Job Description matcher form (GET)
    and processes comparison evaluation (POST).
    """
    watsonx_configured = bool(os.getenv("WATSONX_APIKEY") and os.getenv("WATSONX_PROJECT_ID"))
    
    if request.method == "POST":
        if not watsonx_configured:
            flash("watsonx.ai credentials are not configured in your .env file.", "warning")
            return redirect(url_for("jd_match"))
            
        if "resume" not in request.files or "jd" not in request.files:
            flash("Please upload both your resume and the Job Description file.", "danger")
            return redirect(url_for("jd_match"))
            
        resume_file = request.files["resume"]
        jd_file = request.files["jd"]
        
        if resume_file.filename == "" or jd_file.filename == "":
            flash("Both files must be selected to perform matching.", "danger")
            return redirect(url_for("jd_match"))
            
        # File validations
        res_filename = secure_filename(resume_file.filename)
        _, res_ext = os.path.splitext(res_filename.lower())
        res_ext = res_ext.lstrip(".")
        
        jd_filename = secure_filename(jd_file.filename)
        _, jd_ext = os.path.splitext(jd_filename.lower())
        jd_ext = jd_ext.lstrip(".")
        
        if res_ext != "pdf" or not verify_file_mime_signature(resume_file, "pdf"):
            flash("Resume must be a valid PDF document.", "danger")
            return redirect(url_for("jd_match"))
            
        if jd_ext not in ALLOWED_EXTENSIONS or not verify_file_mime_signature(jd_file, jd_ext):
            flash("Job Description must be a valid PDF, DOCX, or TXT file.", "danger")
            return redirect(url_for("jd_match"))
            
        try:
            # Save files
            res_path = os.path.join(app.config["UPLOAD_FOLDER"], res_filename)
            jd_path = os.path.join(app.config["UPLOAD_FOLDER"], jd_filename)
            resume_file.save(res_path)
            jd_file.save(jd_path)
            
            # Extract texts
            logger.info("Extracting text for Resume vs JD Matching...")
            resume_text = extract_text(res_path)
            
            jd_text = ""
            if jd_ext == "txt":
                with open(jd_path, "r", encoding="utf-8") as f:
                    jd_text = f.read()
            elif jd_ext == "pdf":
                jd_text = extract_text(jd_path)
            elif jd_ext == "docx":
                # lazy import to avoid overhead
                from rag import extract_text_from_docx
                jd_text = extract_text_from_docx(jd_path)
                
            # Perform match analysis via LLM
            logger.info("Calling IBM Granite for Job Description Match report...")
            match_report = generate_jd_match(resume_text, jd_text)
            
            # Cleanup files
            for path in [res_path, jd_path]:
                if os.path.exists(path):
                    os.remove(path)
                    
            return render_template("jd_match_result.html", report=match_report, filename=res_filename)
        except Exception as e:
            logger.error(f"Error matching resume against JD: {e}", exc_info=True)
            flash(f"Matcher evaluation failed: {e}", "danger")
            return redirect(url_for("jd_match"))
            
    return render_template("jd_match.html", watsonx_configured=watsonx_configured)

# ====================================================
# INTERACTIVE MOCK INTERVIEW STATE ROUTER (PHASE 5)
# ====================================================
@app.route("/mock/start", methods=["GET", "POST"])
def mock_start():
    """
    Initializes mock interview state, generating questions via Granite.
    """
    report_id = session.get("report_id")
    sdata = load_session_data(report_id)
    candidate = sdata.get("candidate")
    job_role = session.get("current_job_role")
    company = session.get("current_company")
    difficulty = session.get("current_difficulty")
    
    if not candidate or not job_role:
        flash("Please upload a resume first to start the Mock Interview.", "warning")
        return redirect(url_for("home"))
        
    try:
        logger.info(f"Generating mock questions for candidate {candidate.get('name')} (Role: {job_role})...")
        skills_str = ", ".join(candidate.get("skills", []))
        questions = generate_mock_interview_questions(skills_str, job_role, company, difficulty)
        
        # Save state machine in file cache rather than Flask session
        sdata["mock"] = {
            "questions": questions,
            "current_index": 0,
            "history": [],
            "overall_score": 0,
            "active": True
        }
        save_session_data(report_id, sdata)
        
        session["mock_active"] = True
        return redirect(url_for("mock_question"))
    except Exception as e:
        logger.error(f"Failed to start mock interview session: {e}", exc_info=True)
        flash(f"Failed to start mock interview: {e}", "danger")
        return redirect(url_for("home"))

@app.route("/mock/question", methods=["GET"])
def mock_question():
    """
    Displays the current mock question card.
    """
    report_id = session.get("report_id")
    sdata = load_session_data(report_id)
    mock_state = sdata.get("mock")
    
    if not mock_state or not mock_state.get("active"):
        flash("No active mock interview session found.", "warning")
        return redirect(url_for("home"))
        
    idx = mock_state["current_index"]
    questions = mock_state["questions"]
    
    if idx >= len(questions):
        return redirect(url_for("mock_results"))
        
    q = questions[idx]
    return render_template(
        "mock_interview.html", 
        question=q, 
        index=idx + 1, 
        total=len(questions),
        evaluation=None
    )

@app.route("/mock/submit", methods=["POST"])
def mock_submit():
    """
    Evaluates candidate text answer for the current question using Granite.
    """
    report_id = session.get("report_id")
    sdata = load_session_data(report_id)
    mock_state = sdata.get("mock")
    
    if not mock_state or not mock_state.get("active"):
        return redirect(url_for("home"))
        
    user_answer = request.form.get("answer", "").strip()
    if not user_answer:
        flash("Please type an answer before submitting.", "warning")
        return redirect(url_for("mock_question"))
        
    idx = mock_state["current_index"]
    question = mock_state["questions"][idx]
    
    job_role = session.get("current_job_role")
    company = session.get("current_company")
    difficulty = session.get("current_difficulty")
    
    try:
        logger.info(f"Submitting mock answer for question {idx+1} evaluation...")
        evaluation = evaluate_mock_answer(question, user_answer, job_role, company, difficulty)
        
        # Save Q&A to history log file
        mock_state["history"].append({
            "question": question,
            "answer": user_answer,
            "score": evaluation.get("score", 70),
            "strengths": evaluation.get("strengths", ""),
            "weaknesses": evaluation.get("weaknesses", ""),
            "feedback": evaluation.get("feedback", ""),
            "ideal_answer": evaluation.get("ideal_answer", "")
        })
        save_session_data(report_id, sdata)
        
        # Render feedback evaluation along with Next button
        return render_template(
            "mock_interview.html",
            question=question,
            index=idx + 1,
            total=len(mock_state["questions"]),
            evaluation=evaluation
        )
    except Exception as e:
        logger.error(f"Error evaluating mock answer: {e}", exc_info=True)
        flash(f"Evaluation failed: {e}", "danger")
        return redirect(url_for("mock_question"))

@app.route("/mock/next", methods=["POST"])
def mock_next():
    """
    Increments index pointing to next question or routes to results.
    """
    report_id = session.get("report_id")
    sdata = load_session_data(report_id)
    mock_state = sdata.get("mock")
    
    if not mock_state:
        return redirect(url_for("home"))
        
    mock_state["current_index"] += 1
    save_session_data(report_id, sdata)
    
    if mock_state["current_index"] >= len(mock_state["questions"]):
        return redirect(url_for("mock_results"))
    return redirect(url_for("mock_question"))

@app.route("/mock/results", methods=["GET"])
def mock_results():
    """
    Aggregates full session feedback and renders summary dashboard.
    """
    report_id = session.get("report_id")
    sdata = load_session_data(report_id)
    mock_state = sdata.get("mock")
    
    if not mock_state:
        return redirect(url_for("home"))
        
    history = mock_state.get("history", [])
    if not history:
        flash("Mock interview has no questions submitted.", "warning")
        return redirect(url_for("home"))
        
    # Calculate average score
    total_score = sum(item["score"] for item in history)
    avg_score = int(total_score / len(history)) if history else 0
    
    # Clean up mock memory in file
    sdata.pop("mock", None)
    save_session_data(report_id, sdata)
    
    session.pop("mock_active", None)
    
    return render_template("mock_results.html", history=history, score=avg_score)

# ====================================================
# REPORT DOWNLOAD SERVICES (PHASE 10)
# ====================================================
@app.route("/download/json", methods=["GET"])
def download_json():
    """
    Sends the generated preparation report in raw JSON format.
    """
    report_id = session.get("report_id")
    sdata = load_session_data(report_id)
    report = sdata.get("report")
    
    if not report:
        flash("No generated report found in cache.", "warning")
        return redirect(url_for("home"))
        
    report_json = json.dumps(report, indent=2)
    
    # Serve directly in memory
    from io import BytesIO
    mem = BytesIO()
    mem.write(report_json.encode('utf-8'))
    mem.seek(0)
    
    return send_file(
        mem,
        mimetype="application/json",
        as_attachment=True,
        download_name="interview_report.json"
    )

@app.route("/download/pdf", methods=["GET"])
def download_pdf():
    """
    Triggers dynamic PDF manual compilation using pdf_generator.py.
    """
    report_id = session.get("report_id")
    sdata = load_session_data(report_id)
    report = sdata.get("report")
    candidate = sdata.get("candidate")
    
    job_role = session.get("current_job_role")
    experience_level = session.get("current_experience_level")
    company = session.get("current_company")
    difficulty = session.get("current_difficulty")
    
    if not report or not candidate:
        flash("No active profile session. Please upload your resume first.", "warning")
        return redirect(url_for("home"))
        
    try:
        temp_pdf = os.path.join(app.config["UPLOAD_FOLDER"], "prep_manual.pdf")
        generate_pdf_report(report, candidate, job_role, experience_level, company, difficulty, temp_pdf)
        
        return send_file(
            temp_pdf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="interview_prep_manual.pdf"
        )
    except Exception as e:
        logger.error(f"Error compiling PDF for download: {e}", exc_info=True)
        flash(f"Failed to compile PDF report: {e}", "danger")
        return redirect(url_for("home"))

# Global error page triggers
@app.errorhandler(500)
def server_error(error):
    logger.error(f"Internal 500 error triggered: {error}")
    return render_template("error.html", error_message="Internal Server Error. Please inspect app.log."), 500

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", error_message="Page Not Found"), 404

if __name__ == "__main__":
    # Serve localhost
    app.run(debug=True, host="127.0.0.1", port=5000)
