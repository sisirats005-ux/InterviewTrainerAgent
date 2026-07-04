import os
import json
import logging
import uuid
import time
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from werkzeug.utils import secure_filename
from resume_parser import parse_resume, extract_text
from interview import (
    generate_interview_prep,
    generate_jd_match,
    generate_mock_interview_questions,
    evaluate_mock_answer,
    evaluate_star_answer,
    compute_adaptive_difficulty,
    generate_adaptive_question,
    generate_behavioural_questions,
    evaluate_behavioural_answer,
    generate_learning_plan,
    COMPANY_PROFILES,
    BEHAVIOURAL_COMPETENCIES,
)
from rag import build_vector_db
from pdf_generator import generate_pdf_report
from ats_analyzer import calculate_ats_score
from skill_gap import analyse_skill_gap
from readiness_score import calculate_readiness_score
from analytics import record_session, get_dashboard_data

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
SUPPORTED_COMPANIES = list(COMPANY_PROFILES.keys())
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
    Runs ATS analysis, skill gap analysis, and readiness scoring in addition
    to the existing Granite preparation guide generation.
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
            
            t_start = time.time()

            # --- Phase 1: Resume Parsing ---
            t_parse_start = time.time()
            candidate_data = parse_resume(file_path)
            parse_time = time.time() - t_parse_start
            
            if not candidate_data["skills"] and not candidate_data["raw_text"]:
                flash("Failed to parse text. Please ensure the PDF is not encrypted or blank.", "danger")
                return redirect(url_for("home"))

            # --- Phase 1.1: ATS Score (deterministic, no LLM) ---
            ats_result = calculate_ats_score(candidate_data, job_role)
            logger.info(f"ATS score: {ats_result['ats_score']}/100 for {candidate_data['name']}")

            # --- Phase 1.2: Skill Gap Analysis (deterministic, no LLM) ---
            gap_result = analyse_skill_gap(candidate_data, job_role)
            logger.info(f"Skill gap score: {gap_result['gap_score']}/100 for role '{job_role}'")

            # --- Phase 1.3: Readiness Score (deterministic, no LLM) ---
            readiness_result = calculate_readiness_score(candidate_data, gap_result["gap_score"])
            logger.info(f"Readiness score: {readiness_result['overall_score']}/100")
                
            # --- Granite Generation: Full Interview Prep Guide ---
            logger.info(f"Generating prep guide for {candidate_data['name']} (Role: {job_role}, Company: {company})")
            t_gen_start = time.time()
            report = generate_interview_prep(candidate_data, job_role, experience_level, company, difficulty)
            gen_time = time.time() - t_gen_start
            total_time = time.time() - t_start
            
            timings = report.get("timings", {})
            rag_time_str = timings.get("rag_time", "0.000s")
            llm_time_str = timings.get("llm_time", "0.000s")
            
            logger.info("--- Developer Performance Metrics ---")
            logger.info(f"Resume Parsing Time: {parse_time:.4f}s")
            logger.info(f"ATS/Gap/Readiness Time (deterministic): included in parse")
            logger.info(f"RAG Retrieval Time: {rag_time_str}")
            logger.info(f"Granite API Response Time: {llm_time_str}")
            logger.info(f"Total Request Execution Time: {total_time:.4f}s")
            
            metrics = {
                "parse_time": f"{parse_time:.3f}s",
                "rag_time": rag_time_str,
                "llm_time": llm_time_str,
                "total_time": f"{total_time:.3f}s",
            }
            
            # --- Record analytics ---
            report_id = str(uuid.uuid4())
            try:
                record_session(
                    session_id=report_id,
                    candidate_name=candidate_data.get("name", "Unknown"),
                    job_role=job_role,
                    company=company,
                    ats_score=ats_result["ats_score"],
                    readiness_score=readiness_result["overall_score"],
                    mock_avg_score=None,
                    strong_skills=gap_result["strong_skills"],
                    missing_skills=gap_result["missing_skills"],
                    category_scores=readiness_result["category_scores"],
                )
            except Exception as analytics_err:
                logger.warning(f"Analytics recording failed (non-critical): {analytics_err}")

            # --- Save all session data to disk ---
            session_data = {
                "report": report,
                "candidate": candidate_data,
                "job_role": job_role,
                "experience_level": experience_level,
                "company": company,
                "difficulty": difficulty,
                "metrics": metrics,
                "ats_result": ats_result,
                "gap_result": gap_result,
                "readiness_result": readiness_result,
            }
            save_session_data(report_id, session_data)
            cleanup_old_sessions()
            
            # Store only lightweight references in cookie
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
                metrics=metrics,
                ats_result=ats_result,
                gap_result=gap_result,
                readiness_result=readiness_result,
            )
        except Exception as ex:
            logger.error(f"Error serving interview generation route: {ex}", exc_info=True)
            flash(f"Generation failed: {ex}", "danger")
            return redirect(url_for("home"))

    return render_template(
        "index.html",
        watsonx_configured=watsonx_configured,
        supported_companies=SUPPORTED_COMPANIES,
    )

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
    Applies adaptive difficulty adjustment after every 2 answers.
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
    difficulty = mock_state.get("current_difficulty", session.get("current_difficulty", "Medium"))
    
    try:
        logger.info(f"Submitting mock answer for question {idx+1} (difficulty={difficulty})...")
        evaluation = evaluate_mock_answer(question, user_answer, job_role, company, difficulty)
        
        answer_entry = {
            "question": question,
            "answer": user_answer,
            "score": evaluation.get("score", 70),
            "strengths": evaluation.get("strengths", ""),
            "weaknesses": evaluation.get("weaknesses", ""),
            "feedback": evaluation.get("feedback", ""),
            "ideal_answer": evaluation.get("ideal_answer", ""),
            "difficulty": difficulty,
        }
        mock_state["history"].append(answer_entry)

        # Phase 1.4 — Adaptive difficulty adjustment every 2 answers
        recent_scores = [h["score"] for h in mock_state["history"]]
        new_difficulty = compute_adaptive_difficulty(difficulty, recent_scores)
        if new_difficulty != difficulty:
            mock_state["current_difficulty"] = new_difficulty
            evaluation["difficulty_changed"] = True
            evaluation["new_difficulty"] = new_difficulty
            logger.info(f"Adaptive difficulty changed: {difficulty} → {new_difficulty}")

        save_session_data(report_id, sdata)
        
        return render_template(
            "mock_interview.html",
            question=question,
            index=idx + 1,
            total=len(mock_state["questions"]),
            evaluation=evaluation,
            current_difficulty=new_difficulty,
            user_answer=user_answer,
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
    Updates analytics with the mock interview average score.
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

    # Update analytics with mock performance
    try:
        candidate = sdata.get("candidate", {})
        ats_result = sdata.get("ats_result", {})
        readiness_result = sdata.get("readiness_result", {})
        gap_result = sdata.get("gap_result", {})
        record_session(
            session_id=report_id + "_mock",
            candidate_name=candidate.get("name", "Unknown"),
            job_role=session.get("current_job_role", ""),
            company=session.get("current_company", ""),
            ats_score=ats_result.get("ats_score", 0),
            readiness_score=readiness_result.get("overall_score", avg_score),
            mock_avg_score=avg_score,
            strong_skills=gap_result.get("strong_skills", []),
            missing_skills=gap_result.get("missing_skills", []),
            category_scores=readiness_result.get("category_scores", {}),
        )
    except Exception as e:
        logger.warning(f"Analytics update after mock failed (non-critical): {e}")
    
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
        generate_pdf_report(
            report, candidate, job_role, experience_level, company, difficulty, temp_pdf,
            ats_result=sdata.get("ats_result"),
            gap_result=sdata.get("gap_result"),
            readiness_result=sdata.get("readiness_result"),
        )
        
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

# ====================================================
# ANALYTICS DASHBOARD (PHASE 3.2)
# ====================================================
@app.route("/analytics")
def analytics_dashboard():
    """
    Renders the analytics dashboard with historical performance data.
    """
    data = get_dashboard_data()
    return render_template("analytics.html", data=data)


# ====================================================
# BEHAVIOURAL INTERVIEW MODULE (PHASE 2.3)
# ====================================================
@app.route("/behavioural", methods=["GET", "POST"])
def behavioural_interview():
    """
    GET: Render company-specific behavioural interview question generator.
    POST: Generate and evaluate a behavioural answer using STAR scoring.
    """
    watsonx_configured = bool(os.getenv("WATSONX_APIKEY") and os.getenv("WATSONX_PROJECT_ID"))

    report_id = session.get("report_id")
    sdata = load_session_data(report_id)
    candidate = sdata.get("candidate", {})
    company = session.get("current_company", "IBM")
    job_role = session.get("current_job_role", "Software Engineer")

    if request.method == "POST":
        action = request.form.get("action", "generate")

        if action == "generate":
            if not watsonx_configured:
                flash("watsonx.ai credentials not configured.", "warning")
                return redirect(url_for("behavioural_interview"))
            try:
                questions = generate_behavioural_questions(candidate, company)
                sdata["behavioural_questions"] = questions
                save_session_data(report_id, sdata)
                return render_template(
                    "behavioural.html",
                    questions=questions,
                    company=company,
                    job_role=job_role,
                    supported_companies=SUPPORTED_COMPANIES,
                    watsonx_configured=watsonx_configured,
                )
            except Exception as e:
                logger.error(f"Behavioural question generation error: {e}", exc_info=True)
                flash(f"Generation failed: {e}", "danger")
                return redirect(url_for("behavioural_interview"))

        elif action == "evaluate":
            competency = request.form.get("competency", "Leadership")
            question = request.form.get("question", "")
            answer = request.form.get("answer", "").strip()
            if not answer:
                flash("Please write an answer before submitting.", "warning")
                return redirect(url_for("behavioural_interview"))
            try:
                result = evaluate_behavioural_answer(competency, question, answer, company)
                questions = sdata.get("behavioural_questions", [])
                return render_template(
                    "behavioural.html",
                    questions=questions,
                    company=company,
                    job_role=job_role,
                    supported_companies=SUPPORTED_COMPANIES,
                    watsonx_configured=watsonx_configured,
                    star_result=result,
                    evaluated_question=question,
                    evaluated_answer=answer,
                    evaluated_competency=competency,
                )
            except Exception as e:
                logger.error(f"Behavioural evaluation error: {e}", exc_info=True)
                flash(f"Evaluation failed: {e}", "danger")
                return redirect(url_for("behavioural_interview"))

    return render_template(
        "behavioural.html",
        questions=sdata.get("behavioural_questions"),
        company=company,
        job_role=job_role,
        supported_companies=SUPPORTED_COMPANIES,
        watsonx_configured=watsonx_configured,
    )


# ====================================================
# LEARNING PLAN (PHASE 3.3)
# ====================================================
@app.route("/learning_plan")
def learning_plan():
    """
    Generates a personalised learning plan from the current session data.
    """
    watsonx_configured = bool(os.getenv("WATSONX_APIKEY") and os.getenv("WATSONX_PROJECT_ID"))
    if not watsonx_configured:
        flash("watsonx.ai credentials not configured.", "warning")
        return redirect(url_for("home"))

    report_id = session.get("report_id")
    sdata = load_session_data(report_id)

    if not sdata:
        flash("No active session. Please upload your resume first.", "warning")
        return redirect(url_for("home"))

    candidate = sdata.get("candidate", {})
    job_role = session.get("current_job_role", "Software Engineer")
    company = session.get("current_company", "IBM")
    gap_result = sdata.get("gap_result", {})
    readiness_result = sdata.get("readiness_result", {})

    missing_skills = gap_result.get("missing_skills", []) + gap_result.get("recommended_skills", [])
    # Weak category: those below 65
    weak_cats = [
        cat for cat, score in readiness_result.get("category_scores", {}).items()
        if score < 65
    ]

    try:
        plan = generate_learning_plan(candidate, job_role, company, missing_skills, weak_cats)
        return render_template(
            "learning_plan.html",
            plan=plan,
            candidate=candidate,
            job_role=job_role,
            company=company,
            gap_result=gap_result,
            readiness_result=readiness_result,
        )
    except Exception as e:
        logger.error(f"Learning plan generation error: {e}", exc_info=True)
        flash(f"Learning plan generation failed: {e}", "danger")
        return redirect(url_for("home"))


# ====================================================
# ATS SCORE PAGE (PHASE 1.1 — dedicated view)
# ====================================================
@app.route("/ats")
def ats_score():
    """
    Renders the dedicated ATS score analysis page.
    Reads from session data — requires prior resume upload.
    """
    report_id = session.get("report_id")
    sdata = load_session_data(report_id)

    if not sdata:
        flash("No active session found. Please upload your resume first.", "warning")
        return redirect(url_for("home"))

    ats_result = sdata.get("ats_result", {})
    gap_result = sdata.get("gap_result", {})
    candidate = sdata.get("candidate", {})
    job_role = session.get("current_job_role", "")

    if not ats_result:
        flash("ATS analysis not available. Please re-upload your resume.", "warning")
        return redirect(url_for("home"))

    return render_template(
        "ats_score.html",
        ats_result=ats_result,
        gap_result=gap_result,
        candidate=candidate,
        job_role=job_role,
    )


# ====================================================
# STAR EVALUATOR API ENDPOINT (AJAX-compatible)
# ====================================================
@app.route("/api/star_evaluate", methods=["POST"])
def api_star_evaluate():
    """
    JSON API endpoint for STAR method evaluation.
    Accepts: { question, answer, job_role, company }
    Returns: STAR evaluation JSON
    """
    watsonx_configured = bool(os.getenv("WATSONX_APIKEY") and os.getenv("WATSONX_PROJECT_ID"))
    if not watsonx_configured:
        return jsonify({"error": "watsonx.ai credentials not configured"}), 503

    data = request.get_json(silent=True) or {}
    question = data.get("question", "")
    answer = data.get("answer", "")
    job_role = data.get("job_role", session.get("current_job_role", "Software Engineer"))
    company = data.get("company", session.get("current_company", "IBM"))

    if not question or not answer:
        return jsonify({"error": "question and answer are required"}), 400

    try:
        result = evaluate_star_answer(question, answer, job_role, company)
        return jsonify(result)
    except Exception as e:
        logger.error(f"STAR API evaluation error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


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
