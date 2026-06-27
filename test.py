from granite import generate_response

prompt = """
Generate five Python interview questions for a fresher.
"""

response = generate_response(prompt)

print(response)