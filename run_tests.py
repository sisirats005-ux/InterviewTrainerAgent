import unittest
import os
import json
from app import app
from resume_parser import parse_resume
from granite import generate_response
from rag import retrieve_context, build_vector_db
from interview import calculate_weighted_score, generate_interview_prep

class TestInterviewTrainerSuite(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """
        Setup tests. Ensure sample resume and FAISS database are available.
        """
        cls.sample_pdf = "sample_resume.pdf"
        if not os.path.exists(cls.sample_pdf):
            # Programmatically generate if missing
            from generate_sample_resume import generate_pdf
            generate_pdf()
        
        # Ensure RAG is initialized
        build_vector_db()

    def test_resume_parser(self):
        """
        Test Phase 1: Verify parsing of name, email, phone, github, and skills categories.
        """
        data = parse_resume(self.sample_pdf)
        
        self.assertEqual(data["name"], "Jane Doe")
        self.assertEqual(data["email"], "jane.doe@example.com")
        self.assertEqual(data["phone"], "+1-555-0199")
        self.assertEqual(data["github"], "github.com/janedoe")
        
        # Check categorized skills are populated
        self.assertIn("Python", data["categorized_skills"]["Programming Languages"])
        self.assertIn("PostgreSQL", data["categorized_skills"]["Databases"])
        self.assertIn("AWS", data["categorized_skills"]["Cloud"])
        
        # Verify certifications are parsed
        self.assertTrue(len(data["certifications"]) > 0)
        self.assertIn("AWS Certified", " ".join(data["certifications"]))

    def test_rag_retrieval(self):
        """
        Test Phase 7: Verify FAISS vector index retrieves relevant documentation chunks.
        """
        docs = retrieve_context("What are the ACID properties in database transactions?", k=1)
        self.assertTrue(len(docs) > 0)
        self.assertIn("Atomicity", docs[0].page_content)
        self.assertIn("sql.txt", docs[0].metadata["source"])

    def test_granite_inference(self):
        """
        Verify credentials and connectivity to IBM watsonx.ai.
        """
        watsonx_configured = bool(os.getenv("WATSONX_APIKEY") and os.getenv("WATSONX_PROJECT_ID"))
        if not watsonx_configured:
            self.skipTest("watsonx.ai credentials are not configured. Skipping LLM query test.")
            
        response = generate_response("Write a one-word answer: What is 2 + 2?", temperature=0.1, max_tokens=10)
        self.assertTrue(len(response.strip()) > 0)

    def test_weighted_scoring(self):
        """
        Test Phase 2: Verify weighted score calculations and breakdown ratings.
        """
        mock_profile = {
            "skills": ["Python", "SQL", "Flask", "Docker"],
            "categorized_skills": {
                "Programming Languages": ["Python"],
                "Frameworks": ["Flask"],
                "Databases": ["PostgreSQL"],
                "Cloud": ["Docker"]
            },
            "education": ["B.Tech CS"],
            "experience": ["Internship"],
            "projects": ["Web API Project"],
            "certifications": ["AWS Developer"],
            "name": "Jane Doe",
            "email": "jane@example.com"
        }
        
        score, breakdown = calculate_weighted_score(mock_profile, "Software Engineer", "Junior", "IBM")
        self.assertTrue(10 <= score <= 100)
        self.assertIn("Programming Languages", breakdown)
        self.assertEqual(breakdown["Programming Languages"], 65) # 1 item

    def test_flask_routing(self):
        """
        Test Flask web application routes.
        """
        # Create a testing client
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        client = app.test_client()
        
        # Test main index
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Interview Trainer Agent", response.data)
        
        # Test JD match landing
        response_jd = client.get("/jd_match")
        self.assertEqual(response_jd.status_code, 200)
        self.assertIn(b"Job Description Matcher", response_jd.data)

if __name__ == "__main__":
    unittest.main()
