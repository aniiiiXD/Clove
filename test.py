import os
from dotenv import load_dotenv
from google import genai

# This looks for a file named .env in the same directory and loads the keys
load_dotenv() 

# Now the client will automatically find GOOGLE_API_KEY or GEMINI_API_KEY
client = genai.Client()

# Using the model variable from your .env
model_id = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

response = client.models.generate_content(
    model=model_id,
    contents="How does AI work?"
)

print(response.text)