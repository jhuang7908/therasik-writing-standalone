import os
import argparse
import base64
import requests
from openai import OpenAI
from dotenv import load_dotenv

# Load .env from the same directory as this script
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Generate images using OpenAI gpt-image-2")
    parser.add_argument("--prompt", required=True, help="Image prompt")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--aspect-ratio", default="16:9", help="Aspect ratio (e.g., 16:9, 3:4)")
    
    args = parser.parse_args()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in .env")
        return

    client = OpenAI(api_key=api_key)
    
    print(f"Generating image for prompt: {args.prompt}...")
    
    try:
        response = client.images.generate(
            model="gpt-image-2",
            prompt=args.prompt,
            size="1024x1024",
            n=1
        )
        
        data = response.data[0]
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        
        if hasattr(data, 'url') and data.url:
            print(f"Downloading image from {data.url}...")
            img_resp = requests.get(data.url)
            img_resp.raise_for_status()
            with open(args.output, "wb") as f:
                f.write(img_resp.content)
        elif hasattr(data, 'b64_json') and data.b64_json:
            print("Saving image from base64 data...")
            image_data = base64.b64decode(data.b64_json)
            with open(args.output, "wb") as f:
                f.write(image_data)
        else:
            print("Error: No image URL or base64 data found in response.")
            print(f"Response data: {data}")
            return
        
        print(f"Success! Image saved to {args.output}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
