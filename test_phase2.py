import os
from resume_parser import parse_resume
from granite import generate_response

def test_integration():
    print("=== INTEGRATION TEST: RESUME PARSING & GRANITE ===")
    
    # 1. Parse the resume
    resume_path = "sample_resume.pdf"
    if not os.path.exists(resume_path):
        print(f"Error: {resume_path} not found. Please run generate_sample_resume.py first.")
        return
        
    print(f"Step 1: Parsing resume '{resume_path}'...")
    resume_data = parse_resume(resume_path)
    print(f"Extracted Skills: {resume_data['skills']}")
    
    # 2. Construct a test prompt using the extracted skills
    skills_str = ", ".join(resume_data['skills'][:5]) # Use first 5 skills
    prompt = f"""
    The candidate has the following technical skills: {skills_str}.
    Based on these skills, generate exactly one technical interview question and its model answer.
    Format your response as:
    Question: [Question text]
    Answer: [Answer text]
    """
    
    # 3. Call IBM watsonx.ai model
    print("\nStep 2: Sending prompt to IBM Granite model...")
    try:
        response = generate_response(prompt, temperature=0.7, max_tokens=300)
        print("\n=== Model Response ===")
        print(response)
        print("\nTest passed successfully!")
    except Exception as e:
        print(f"\nTest failed: {e}")

if __name__ == "__main__":
    test_integration()
