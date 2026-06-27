import fitz

def generate_pdf():
    # Create a new empty PDF document
    doc = fitz.open()
    
    # Add a new blank page (standard letter size: 612 x 792 points)
    page = doc.new_page(width=612, height=792)
    
    # Define coordinate margins
    x_margin = 54
    y_cursor = 54
    
    # Draw header (Name)
    page.insert_text((x_margin, y_cursor), "Jane Doe", fontsize=24, color=(0.1, 0.1, 0.4))
    y_cursor += 30
    
    # Contact info
    contact_text = "Email: jane.doe@example.com | Phone: +1-555-0199 | GitHub: github.com/janedoe | Location: New York, NY"
    page.insert_text((x_margin, y_cursor), contact_text, fontsize=9, color=(0.3, 0.3, 0.3))
    y_cursor += 30
    
    # Divider line
    shape = page.new_shape()
    shape.draw_line(fitz.Point(x_margin, y_cursor), fitz.Point(612 - x_margin, y_cursor))
    shape.finish(color=(0.7, 0.7, 0.7), width=1)
    shape.commit()
    y_cursor += 20
    
    # Skills Section
    page.insert_text((x_margin, y_cursor), "TECHNICAL SKILLS", fontsize=13, color=(0.1, 0.1, 0.4))
    y_cursor += 18
    skills = [
        "Languages: Python, SQL, JavaScript, HTML, CSS",
        "Frameworks & Libraries: Flask, Django, LangChain, React, Bootstrap, Pandas",
        "Databases & Vector Stores: PostgreSQL, MySQL, SQLite, FAISS, Redis",
        "Tools & Technologies: Git, Docker, AWS, RESTful APIs, PyMuPDF, Virtualenv"
    ]
    for skill in skills:
        page.insert_text((x_margin + 15, y_cursor), f"\u2022  {skill}", fontsize=10)
        y_cursor += 15
    y_cursor += 10
    
    # Experience Section
    page.insert_text((x_margin, y_cursor), "WORK EXPERIENCE", fontsize=13, color=(0.1, 0.1, 0.4))
    y_cursor += 18
    
    # Job 1
    page.insert_text((x_margin, y_cursor), "Software Engineer Intern - TechSolutions Inc.", fontsize=11, color=(0.2, 0.2, 0.2))
    page.insert_text((612 - x_margin - 120, y_cursor), "Jan 2025 - Present", fontsize=10, color=(0.4, 0.4, 0.4))
    y_cursor += 15
    bullets_job1 = [
        "Developed and optimized RESTful API endpoints using Python Flask, improving request speeds by 20%.",
        "Implemented database schema changes and wrote complex SQL queries in PostgreSQL for data analysis.",
        "Collaborated with frontend developers to build interactive analytics dashboards using React and Bootstrap.",
        "Wrote unit tests and automated integration testing, which increased test coverage from 65% to 85%."
    ]
    for bullet in bullets_job1:
        page.insert_text((x_margin + 15, y_cursor), f"\u2022  {bullet}", fontsize=9.5)
        y_cursor += 14
    y_cursor += 12
    
    # Projects Section
    page.insert_text((x_margin, y_cursor), "PERSONAL PROJECTS", fontsize=13, color=(0.1, 0.1, 0.4))
    y_cursor += 18
    
    # Project 1
    page.insert_text((x_margin, y_cursor), "Interview Trainer Agent (Flask & LangChain & FAISS)", fontsize=11, color=(0.2, 0.2, 0.2))
    page.insert_text((612 - x_margin - 80, y_cursor), "May 2026", fontsize=10, color=(0.4, 0.4, 0.4))
    y_cursor += 15
    bullets_proj1 = [
        "Built a Retrieval-Augmented Generation (RAG) tool using FAISS to query technical databases for interview preparation.",
        "Utilized IBM watsonx.ai Granite models to generate candidate readiness scores and customized HR/behavioral questions.",
        "Implemented resume parsing using PyMuPDF to extract candidate skill arrays and project highlights."
    ]
    for bullet in bullets_proj1:
        page.insert_text((x_margin + 15, y_cursor), f"\u2022  {bullet}", fontsize=9.5)
        y_cursor += 14
    y_cursor += 12
    
    # Education Section
    page.insert_text((x_margin, y_cursor), "EDUCATION", fontsize=13, color=(0.1, 0.1, 0.4))
    y_cursor += 18
    
    page.insert_text((x_margin, y_cursor), "Bachelor of Technology in Computer Science & Engineering", fontsize=11, color=(0.2, 0.2, 0.2))
    page.insert_text((612 - x_margin - 120, y_cursor), "Graduated: May 2025", fontsize=10, color=(0.4, 0.4, 0.4))
    y_cursor += 15
    page.insert_text((x_margin + 15, y_cursor), "State University of Technology | GPA: 3.8 / 4.0 | Major Coursework: DBMS, OS, Data Structures, Algorithms", fontsize=10)
    y_cursor += 20
    
    # Certifications Section
    page.insert_text((x_margin, y_cursor), "CERTIFICATIONS", fontsize=13, color=(0.1, 0.1, 0.4))
    y_cursor += 18
    page.insert_text((x_margin + 15, y_cursor), "\u2022  AWS Certified Solutions Architect - Associate (Feb 2026)", fontsize=10)
    y_cursor += 14
    page.insert_text((x_margin + 15, y_cursor), "\u2022  Certified Kubernetes Administrator (CKA) - Linux Foundation (Apr 2026)", fontsize=10)
    y_cursor += 20
    
    # Achievements Section
    page.insert_text((x_margin, y_cursor), "ACHIEVEMENTS", fontsize=13, color=(0.1, 0.1, 0.4))
    y_cursor += 18
    page.insert_text((x_margin + 15, y_cursor), "\u2022  First Place - University Hackathon (Out of 120 teams) (Oct 2024)", fontsize=10)
    y_cursor += 14
    page.insert_text((x_margin + 15, y_cursor), "\u2022  Top 5% performer in National Coding Assessment test (2025)", fontsize=10)
    
    # Save the document
    doc.save("sample_resume.pdf")
    doc.close()
    print("Success: Generated 'sample_resume.pdf'")

if __name__ == "__main__":
    generate_pdf()
