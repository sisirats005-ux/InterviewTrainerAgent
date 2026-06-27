import os
from dotenv import load_dotenv
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

# Load environment variables from .env file
load_dotenv()

# Read configurations securely from environment variables
API_KEY = os.getenv("WATSONX_APIKEY")
PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
URL = os.getenv("WATSONX_URL", "https://eu-de.ml.cloud.ibm.com")
MODEL_ID = "ibm/granite-4-h-small"

# Ensure credentials exist before initializing to prevent immediate crash
if not API_KEY or not PROJECT_ID:
    print("\n[WARNING] watsonx.ai Credentials not fully configured in environment variables.")
    print("Please ensure WATSONX_APIKEY and WATSONX_PROJECT_ID are set in your .env file.\n")

def get_watsonx_model(temperature=0.7, max_tokens=1500):
    """
    Initializes and returns the watsonx.ai ModelInference client.
    
    Args:
        temperature (float): The generation temperature (default: 0.7).
        max_tokens (int): The maximum number of new tokens to generate (default: 1500).
        
    Returns:
        ModelInference: The initialized inference client, or None if credentials are missing.
    """
    if not API_KEY or not PROJECT_ID:
        raise ValueError("IBM watsonx.ai API_KEY and PROJECT_ID must be set in the .env file.")
        
    credentials = Credentials(
        url=URL,
        api_key=API_KEY
    )
    
    # Configure generation parameters
    params = {
        GenParams.MAX_NEW_TOKENS: max_tokens,
        GenParams.TEMPERATURE: temperature,
        GenParams.MIN_NEW_TOKENS: 1,
        GenParams.DECODING_METHOD: "sample"  # Required when temperature is used
    }
    
    return ModelInference(
        model_id=MODEL_ID,
        credentials=credentials,
        project_id=PROJECT_ID,
        params=params
    )

def generate_response(prompt, temperature=0.7, max_tokens=1500):
    """
    Generates a text completion from the IBM Granite model.
    
    Args:
        prompt (str): The prompt text to send to the model.
        temperature (float): Controls response randomness.
        max_tokens (int): Maximum new tokens to generate.
        
    Returns:
        str: The generated text response from Granite.
    """
    try:
        model = get_watsonx_model(temperature=temperature, max_tokens=max_tokens)
        response = model.generate_text(prompt=prompt)
        return response
    except Exception as e:
        error_msg = f"Error generating response from IBM Granite model: {e}"
        print(error_msg)
        raise RuntimeError(error_msg)

if __name__ == "__main__":
    # Test credentials and generation
    print("Testing IBM watsonx.ai connectivity...")
    test_prompt = "Hello! Tell me in one short sentence what model you are."
    try:
        response = generate_response(test_prompt, temperature=0.2, max_tokens=100)
        print("\n--- Model Response ---")
        print(response)
    except Exception as e:
        print(f"\nConnection Test Failed: {e}")