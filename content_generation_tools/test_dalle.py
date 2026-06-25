import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in .env")
    exit(1)

print("Testing OpenAI DALL-E 3 Image Generation...")
client = OpenAI(api_key=api_key)

try:
    response = client.images.generate(
        model="dall-e-2",
        prompt="A highly professional and aesthetic cover image for a scientific whitepaper about Antibody Engineering and AI Discovery, tech-blue style, minimal, geometric.",
        size="1024x1024",
        n=1,
    )
    
    image_url = response.data[0].url
    print(f"Success! Image generated successfully.")
    print(f"Image URL: {image_url}")
    print("You can click the link above to view the generated image.")
except Exception as e:
    print(f"Error occurred: {e}")
