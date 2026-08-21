import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from backend or root
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT_DIR = os.path.dirname(_BASE_DIR)

load_dotenv(os.path.join(_BASE_DIR, ".env"))
load_dotenv(os.path.join(_ROOT_DIR, ".env"))

print("GROQ_API_KEY present:", bool(os.getenv("GROQ_API_KEY")))

try:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    chat_completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": "Hello, are you online?"}]
    )
    print("Success! Groq response:")
    print(chat_completion.choices[0].message.content)
except Exception as e:
    print("Failed to run Groq completion:", e)
