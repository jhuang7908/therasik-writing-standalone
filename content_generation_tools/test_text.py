import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

print("Testing OpenAI Text Generation...")
try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello!"}]
    )
    print(f"Success! Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"Error occurred: {e}")
