import openai
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env")

openai.api_key = OPENAI_API_KEY

def gpt4o_image_prompt(prompt, base64_image):
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]
        }
    ]

def call_gpt4o(prompt, base64_images=None):
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    if base64_images:
        messages[0]["content"] += [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}} for img in base64_images]

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            max_tokens=900
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[OpenAI API Error] {e}"
