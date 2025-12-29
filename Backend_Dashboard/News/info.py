# News/info.py
import os
import json
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the API key from .env
GROQ_API_KEY = os.getenv("GROQ")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ API key not found. Please set it in the .env file as GROQ=your_key")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

def get_current_natural_disasters():
    """
    Fetches latest ongoing natural disasters using Groq AI with up-to-date knowledge.
    Returns structured JSON.
    """
    prompt = """
You are a professional disaster news aggregator.
Provide a summary of the most significant ongoing or very recent natural disasters worldwide as of today.

Include only real, verified events from trusted sources (UN, ReliefWeb, GDACS, FEMA, Reuters, BBC, etc.).

Return ONLY valid JSON in this exact format — no extra text:

{
  "as_of": "YYYY-MM-DD",
  "total_disasters": number,
  "disasters": [
    {
      "headline": "Clear and concise headline",
      "type": "Flood / Earthquake / Cyclone / Wildfire / etc.",
      "locations": ["Country", "Region"],
      "summary": "Brief impact summary including deaths, affected people, damage",
      "source": "Main sources",
      "date": "Start or key date"
    }
  ]
}
"""

    try:
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise JSON generator. Always respond with only valid JSON and nothing else."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.4,
            max_tokens=1024,
            top_p=0.95
        )

        content = completion.choices[0].message.content.strip()

        # Clean common issues (like markdown code blocks)
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        return json.loads(content)

    except json.JSONDecodeError as e:
        return {
            "error": "Invalid JSON from AI model",
            "raw_response": content,
            "parse_error": str(e)
        }
    except Exception as e:
        return {
            "error": "Failed to fetch disaster news",
            "details": str(e)
        }