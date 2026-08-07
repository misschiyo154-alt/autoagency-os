import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Load Environment Variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

# Create Gemini Client
client = genai.Client(api_key=api_key)

# User Inputs
business_name = input("Business Name: ")
business_type = input("Business Type: ")
location = input("Location: ")

# Read Prompt File
with open("03-prompts/website-generator.md", "r", encoding="utf-8") as f:
    prompt_template = f.read()

# Replace Variables
prompt = prompt_template.format(
    business_name=business_name,
    business_type=business_type,
    location=location
)

# Generate Website
try:
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
except Exception as e:
    print("\n❌ Gemini Error:")
    print(e)
    exit()

html = response.text

# Remove Markdown if Gemini returns it
if html.startswith("```html"):
    html = html.replace("```html", "").replace("```", "").strip()

# Save Website
output = Path("02-websites/generated/index.html")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(html, encoding="utf-8")

print("\n✅ Website Generated Successfully!")
print(f"📁 Saved to: {output}")