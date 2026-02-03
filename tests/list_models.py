import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

if not api_key:
    print("API Key not found in .env")
    exit()

client = genai.Client(api_key=api_key)

try:
    print("Listing available models...")
    for model in client.models.list():
        print(f"Model: {model.name}")
        # print(f"  Snippet: {model}")
except Exception as e:
    print(f"Error listing models: {e}")
