import fitz
import os
import re

def clean_text_for_pdf(text):
    """
    Cleans Unicode characters that are not supported by the default Helvetica font.
    """
    if not text:
        return ""
    text = text.replace('\u2022', '-')
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u2014', '-')
    # Remove any other non-ASCII characters if necessary
    return text.encode('ascii', 'ignore').decode('ascii')

def generate_pdf_report(report, candidate, job_role, experience_level, company, difficulty, output_path="report.pdf"):
    """
    Generates a beautifully formatted PDF report containing:
    1. Overall Readiness Score & Skill Breakdown.
    2. Candidate Resume Summary.
    3. Technical, HR, and Behavioral Questions & Answers.
    4. Preparation Tips & Actionable Recommendations.
    
    Args:
        report (dict): The generated interview preparation report.
        candidate (dict): The parsed candidate resume details.
        job_role (str): The target job role.
        experience_level (str): The target experience level.
        company (str): The target company name.
        difficulty (str): The interview difficulty tier.
        output_path (str): The path to save the generated PDF.
        
    Returns:
        str: Absolute path to the saved PDF file.
    """
    doc = fitz.open()
    
    # ----------------------------------------------------
    # PAGE 1: TITLE & CANDIDATE ALIGNMENT ASSESSMENT
    # ----------------------------------------------------
    page1 = doc.new_page(width=612, height=792)
    x_margin = 54
    y_cursor = 60
    
    # Page Title
    page1.insert_text((x_margin, y_cursor), "INTERVIEW PREPARATION MANUAL", fontsize=18, color=(0.1, 0.1, 0.4), fontname="helvetica-bold")
    y_cursor += 20
    subtitle = f"Position: {job_role} | Level: {experience_level} | Target: {company} ({difficulty})"
    page1.insert_text((x_margin, y_cursor), clean_text_for_pdf(subtitle), fontsize=10, color=(0.3, 0.3, 0.3), fontname="helvetica-oblique")
    y_cursor += 15
    
    # Draw horizontal divider
    shape = page1.new_shape()
    shape.draw_line(fitz.Point(x_margin, y_cursor), fitz.Point(612 - x_margin, y_cursor))
    shape.finish(color=(0.7, 0.7, 0.7), width=1)
    shape.commit()
    y_cursor += 25
    
    # Readiness Score Block
    score_box_height = 80
    shape = page1.new_shape()
    shape.draw_rect(fitz.Rect(x_margin, y_cursor, 612 - x_margin, y_cursor + score_box_height))
    # Light emerald green background
    shape.finish(color=(0.92, 0.98, 0.95), fill=(0.92, 0.98, 0.95))
    shape.commit()
    
    page1.insert_text((x_margin + 20, y_cursor + 35), "INTERVIEW READINESS SCORE", fontsize=12, color=(0.06, 0.45, 0.3), fontname="helvetica-bold")
    score_str = f"{report.get('overall_score', 80)}%"
    page1.insert_text((420, y_cursor + 50), score_str, fontsize=36, color=(0.38, 0.4, 0.94), fontname="helvetica-bold")
    
    # Text fit status
    fit_status = "HIGH ALIGNMENT" if report.get('overall_score', 80) >= 85 else "MODERATE ALIGNMENT" if report.get('overall_score', 80) >= 65 else "DEVELOPMENT REQUIRED"
    page1.insert_text((x_margin + 20, y_cursor + 55), f"Status: {fit_status}", fontsize=9, color=(0.4, 0.4, 0.4), fontname="helvetica-bold")
    y_cursor += score_box_height + 30
    
    # Section: Key Strengths & Weaknesses
    page1.insert_text((x_margin, y_cursor), "STRENGTHS & GAP ANALYSIS", fontsize=13, color=(0.1, 0.1, 0.4), fontname="helvetica-bold")
    y_cursor += 20
    
    # Strengths
    page1.insert_text((x_margin, y_cursor), "Core Strengths:", fontsize=10, color=(0.1, 0.5, 0.1), fontname="helvetica-bold")
    y_cursor += 15
    for strg in report.get("strengths", [])[:3]:
        page1.insert_text((x_margin + 15, y_cursor), f"- {clean_text_for_pdf(strg)}", fontsize=9.5, color=(0.2, 0.2, 0.2), fontname="helvetica")
        y_cursor += 14
    y_cursor += 10
    
    # Weaknesses
    page1.insert_text((x_margin, y_cursor), "Areas for Development:", fontsize=10, color=(0.8, 0.1, 0.1), fontname="helvetica-bold")
    y_cursor += 15
    for weak in report.get("weaknesses", [])[:3]:
        page1.insert_text((x_margin + 15, y_cursor), f"- {clean_text_for_pdf(weak)}", fontsize=9.5, color=(0.2, 0.2, 0.2), fontname="helvetica")
        y_cursor += 14
    y_cursor += 10
    
    # Recommendations
    page1.insert_text((x_margin, y_cursor), "Actionable Recommendations:", fontsize=10, color=(0.1, 0.1, 0.4), fontname="helvetica-bold")
    y_cursor += 15
    for rec in report.get("recommendations", [])[:4]:
        page1.insert_text((x_margin + 15, y_cursor), f"- {clean_text_for_pdf(rec)}", fontsize=9.5, color=(0.2, 0.2, 0.2), fontname="helvetica")
        y_cursor += 14
        
    page1.insert_text((612/2 - 20, 750), "Page 1", fontsize=8, color=(0.5, 0.5, 0.5), fontname="helvetica")
    
    # ----------------------------------------------------
    # PAGE 2: CANDIDATE PROFILE SUMMARY
    # ----------------------------------------------------
    page2 = doc.new_page(width=612, height=792)
    y_cursor = 60
    
    page2.insert_text((x_margin, y_cursor), "CANDIDATE PROFILE SUMMARY", fontsize=15, color=(0.1, 0.1, 0.4), fontname="helvetica-bold")
    y_cursor += 15
    page2.insert_text((x_margin, y_cursor), f"Candidate: {candidate.get('name', 'Jane Doe')}", fontsize=11, color=(0.2, 0.2, 0.2), fontname="helvetica-bold")
    y_cursor += 8
    
    contact_text = f"Email: {candidate.get('email')} | Phone: {candidate.get('phone')} | GitHub: {candidate.get('github')}"
    page2.insert_text((x_margin, y_cursor), clean_text_for_pdf(contact_text), fontsize=9, color=(0.4, 0.4, 0.4))
    y_cursor += 15
    
    shape = page2.new_shape()
    shape.draw_line(fitz.Point(x_margin, y_cursor), fitz.Point(612 - x_margin, y_cursor))
    shape.finish(color=(0.8, 0.8, 0.8), width=1)
    shape.commit()
    y_cursor += 20
    
    # Skills Categories list
    page2.insert_text((x_margin, y_cursor), "Categorized Technical Skills:", fontsize=11, color=(0.1, 0.1, 0.4), fontname="helvetica-bold")
    y_cursor += 18
    
    cat_skills = candidate.get("categorized_skills", {})
    for category, list_s in cat_skills.items():
        if list_s:
            cat_str = f"{category}: {', '.join(list_s)}"
            page2.insert_text((x_margin + 15, y_cursor), clean_text_for_pdf(cat_str), fontsize=9.5, color=(0.2, 0.2, 0.2), fontname="helvetica")
            y_cursor += 15
    y_cursor += 10
    
    # Education
    page2.insert_text((x_margin, y_cursor), "Education Details:", fontsize=11, color=(0.1, 0.1, 0.4), fontname="helvetica-bold")
    y_cursor += 18
    for edu in candidate.get("education", [])[:4]:
        page2.insert_text((x_margin + 15, y_cursor), clean_text_for_pdf(edu), fontsize=9.5, color=(0.2, 0.2, 0.2), fontname="helvetica")
        y_cursor += 15
    y_cursor += 10
    
    # Missing Skills
    page2.insert_text((x_margin, y_cursor), "Identified Missing Critical Skills:", fontsize=11, color=(0.8, 0.1, 0.1), fontname="helvetica-bold")
    y_cursor += 18
    missing = report.get("missing_skills", [])
    if missing:
        missing_str = ", ".join(missing)
        page2.insert_text((x_margin + 15, y_cursor), clean_text_for_pdf(missing_str), fontsize=9.5, color=(0.2, 0.2, 0.2), fontname="helvetica")
    else:
        page2.insert_text((x_margin + 15, y_cursor), "None identified. Strong core skill alignment.", fontsize=9.5, color=(0.2, 0.2, 0.2), fontname="helvetica-oblique")
        
    page2.insert_text((612/2 - 20, 750), "Page 2", fontsize=8, color=(0.5, 0.5, 0.5), fontname="helvetica")
    
    # ----------------------------------------------------
    # PAGE 3: TECHNICAL QUESTIONS & ANSWERS
    # ----------------------------------------------------
    page3 = doc.new_page(width=612, height=792)
    y_cursor = 60
    
    page3.insert_text((x_margin, y_cursor), "TECHNICAL INTERVIEW QUESTIONS", fontsize=15, color=(0.1, 0.1, 0.4), fontname="helvetica-bold")
    y_cursor += 15
    
    shape = page3.new_shape()
    shape.draw_line(fitz.Point(x_margin, y_cursor), fitz.Point(612 - x_margin, y_cursor))
    shape.finish(color=(0.8, 0.8, 0.8), width=1)
    shape.commit()
    y_cursor += 20
    
    for idx, item in enumerate(report.get("technical_questions", [])):
        q_text = f"Q{idx+1}: {item.get('question')}"
        a_text = f"Answer: {item.get('answer')}"
        
        # Write Question (Helvetica Bold)
        page3.insert_textbox(fitz.Rect(x_margin, y_cursor, 612 - x_margin, y_cursor + 35), clean_text_for_pdf(q_text), fontsize=10, fontname="helvetica-bold", color=(0.1, 0.1, 0.1))
        y_cursor += 38
        
        # Write Answer (Helvetica Regular)
        page3.insert_textbox(fitz.Rect(x_margin + 15, y_cursor, 612 - x_margin, y_cursor + 90), clean_text_for_pdf(a_text), fontsize=9, fontname="helvetica", color=(0.3, 0.3, 0.3))
        y_cursor += 95
        
    page3.insert_text((612/2 - 20, 750), "Page 3", fontsize=8, color=(0.5, 0.5, 0.5), fontname="helvetica")
    
    # ----------------------------------------------------
    # PAGE 4: BEHAVIORAL & HR QUESTIONS
    # ----------------------------------------------------
    page4 = doc.new_page(width=612, height=792)
    y_cursor = 60
    
    page4.insert_text((x_margin, y_cursor), "BEHAVIORAL & HR INTERVIEW QUESTIONS", fontsize=15, color=(0.1, 0.1, 0.4), fontname="helvetica-bold")
    y_cursor += 15
    
    shape = page4.new_shape()
    shape.draw_line(fitz.Point(x_margin, y_cursor), fitz.Point(612 - x_margin, y_cursor))
    shape.finish(color=(0.8, 0.8, 0.8), width=1)
    shape.commit()
    y_cursor += 20
    
    # Behavioral Questions (2)
    for idx, item in enumerate(report.get("behavioral_questions", [])):
        q_text = f"Behavioral Q{idx+1}: {item.get('question')}"
        a_text = f"Answer: {item.get('answer')}"
        
        page4.insert_textbox(fitz.Rect(x_margin, y_cursor, 612 - x_margin, y_cursor + 35), clean_text_for_pdf(q_text), fontsize=10, fontname="helvetica-bold", color=(0.1, 0.1, 0.1))
        y_cursor += 38
        page4.insert_textbox(fitz.Rect(x_margin + 15, y_cursor, 612 - x_margin, y_cursor + 90), clean_text_for_pdf(a_text), fontsize=9, fontname="helvetica", color=(0.3, 0.3, 0.3))
        y_cursor += 95
        
    # HR Questions (2)
    for idx, item in enumerate(report.get("hr_questions", [])):
        q_text = f"Cultural Fit Q{idx+1}: {item.get('question')}"
        a_text = f"Answer: {item.get('answer')}"
        
        page4.insert_textbox(fitz.Rect(x_margin, y_cursor, 612 - x_margin, y_cursor + 35), clean_text_for_pdf(q_text), fontsize=10, fontname="helvetica-bold", color=(0.1, 0.1, 0.1))
        y_cursor += 38
        page4.insert_textbox(fitz.Rect(x_margin + 15, y_cursor, 612 - x_margin, y_cursor + 90), clean_text_for_pdf(a_text), fontsize=9, fontname="helvetica", color=(0.3, 0.3, 0.3))
        y_cursor += 95
        
    page4.insert_text((612/2 - 20, 750), "Page 4", fontsize=8, color=(0.5, 0.5, 0.5), fontname="helvetica")
    
    # Save the PDF to directory path
    doc.save(output_path)
    doc.close()
    
    return os.path.abspath(output_path)

if __name__ == "__main__":
    # Test generation with mock data
    mock_report = {
        "overall_score": 88,
        "strengths": ["Strong Python programming skills.", "Understands FAISS vector search setups."],
        "weaknesses": ["Lacks experience in multi-region cloud deployment."],
        "recommendations": ["Earn AWS Solutions Architect certificate."],
        "technical_questions": [
            {"question": "How does python manage reference counts?", "answer": "Objects are deallocated immediately when references drop to 0."}
        ],
        "behavioral_questions": [
            {"question": "Tell me about a time you solved a database error.", "answer": "I rewrote SQL queries to remove redundant table scans, reducing load."}
        ],
        "hr_questions": [
            {"question": "Why Google?", "answer": "I align with engineering transparency and scaling requirements."}
        ],
        "missing_skills": ["Docker", "AWS Cloud"]
    }
    
    mock_candidate = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "+1-555-0100",
        "github": "github.com/janedoe",
        "categorized_skills": {
            "Programming Languages": ["Python", "SQL"],
            "Frameworks": ["Flask"],
            "Databases": ["PostgreSQL", "FAISS"]
        },
        "education": ["B.Tech Computer Science - State University"],
        "experience": ["Intern at TechSolutions Inc."]
    }
    
    out = "test_manual.pdf"
    res_path = generate_pdf_report(mock_report, mock_candidate, "Backend Developer", "Junior", "Google", "Hard", out)
    print(f"Mock manual generated successfully at: {res_path}")
    if os.path.exists(out):
        os.remove(out)
