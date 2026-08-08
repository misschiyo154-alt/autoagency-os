import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# ==========================
# Load Environment
# ==========================

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ==========================
# Business Details
# ==========================

if len(sys.argv) == 5:
    business_name = sys.argv[1]
    business_type = sys.argv[2]
    location = sys.argv[3]
    demo_url = sys.argv[4]
else:
    business_name = input("Business Name: ")
    business_type = input("Business Type: ")
    location = input("Location: ")
    demo_url = input("Demo Website URL: ")


# ==========================
# Choose Email Template
# ==========================

print("\nChoose Email Template:")
print("1. Original")
print("2. Short & Friendly")

template_choice = input("Enter 1 or 2: ").strip()

if template_choice == "2":
    prompt_path = Path("04-emails/templates/cold_2.md")
else:
    prompt_path = Path("04-emails/email-prompt.md")


# ==========================
# Load Prompt Template
# ==========================

with open(prompt_path, "r", encoding="utf-8") as file:
    prompt = file.read()


# ==========================
# Replace Variables
# ==========================

prompt = prompt.format(
    business_name=business_name,
    business_type=business_type,
    location=location,
    demo_url=demo_url
)


# ==========================
# Generate Email
# ==========================

try:
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

    email = response.text.strip()

except Exception as e:
    print("\n❌ Gemini Error:")
    print(e)
    sys.exit(1)


# ==========================
# Remove Markdown
# ==========================

if email.startswith("```"):
    email = email.replace("```text", "")
    email = email.replace("```", "")
    email = email.strip()


# ==========================
# Save Email
# ==========================

output_dir = Path("04-emails/generated")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "email.txt"

with open(output_file, "w", encoding="utf-8") as file:
    file.write(email)


# ==========================
# Success Message
# ==========================

print("\n===============================")
print("✅ Email Generated Successfully!")
print("===============================")
print(f"Saved to : {output_file}")
print("\n----------- EMAIL -----------\n")
print(email)