import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# ==========================
# Load Environment Variables
# ==========================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

# ==========================
# Create Gemini Client
# ==========================

client = genai.Client(
    api_key=api_key
)

# ==========================
# User Inputs
# ==========================

if len(sys.argv) == 4:

    business_name = sys.argv[1]
    business_type = sys.argv[2]
    location = sys.argv[3]

else:

    business_name = input("Business Name: ")
    business_type = input("Business Type: ")
    location = input("Location: ")

# ==========================
# Read Prompt File
# ==========================

with open(
    "03-prompts/website-generator.md",
    "r",
    encoding="utf-8"
) as f:

    prompt_template = f.read()

# ==========================
# Replace Variables
# ==========================

prompt = prompt_template.format(
    business_name=business_name,
    business_type=business_type,
    location=location
)

# ==========================
# Generate Website
# ==========================

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

# ==========================
# Remove Markdown
# ==========================

if html.startswith("```html"):

    html = (
        html
        .replace("```html", "")
        .replace("```", "")
        .strip()
    )

# ==========================
# Create Safe Folder Name
# ==========================

slug = business_name.lower()

slug = slug.replace(
    "&",
    "and"
)

slug = re.sub(
    r"[^a-z0-9]+",
    "-",
    slug
)

slug = slug.strip("-")

# ==========================
# Save Website
# ==========================

client_folder = (
    Path("02-websites")
    / slug
)

client_folder.mkdir(
    parents=True,
    exist_ok=True
)

output = (
    client_folder
    / "index.html"
)

output.write_text(
    html,
    encoding="utf-8"
)

# ==========================
# Save Latest Generated Website
# ==========================

latest_output = (
    Path("02-websites")
    / "generated"
    / "index.html"
)

latest_output.parent.mkdir(
    parents=True,
    exist_ok=True
)

latest_output.write_text(
    html,
    encoding="utf-8"
)

# ==========================
# Demo URL
# ==========================

demo_url = (
    f"https://autoagency-os.pages.dev/"
    f"{slug}/"
)

# ==========================
# Result
# ==========================

print(
    f"📁 Latest Website Saved : "
    f"{latest_output}"
)

print(
    "\n✅ Website Generated Successfully!"
)

print(
    f"📁 Saved to: {output}"
)

print(
    f"🌐 Demo URL: {demo_url}"
)