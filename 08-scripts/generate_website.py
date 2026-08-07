import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

business_name = input("Business Name: ")
business_type = input("Business Type: ")
location = input("Location: ")

prompt = f"""
You are an expert web designer.

Generate ONE complete production-ready index.html page.

Business Name: {business_name}
Business Type: {business_type}
Location: {location}

Requirements:
- HTML5
- Tailwind CSS CDN
- Responsive
- Modern UI
- Hero
- About
- Services
- Testimonials
- FAQ
- Contact Form
- Footer

Return ONLY HTML.
"""

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=prompt,
)

html = response.text

if html.startswith("```html"):
    html = html.replace("```html", "").replace("```", "").strip()

output = Path("02-websites/generated/index.html")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(html, encoding="utf-8")

print("✅ Website Generated Successfully!")
print(f"Saved to: {output}")