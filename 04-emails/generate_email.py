import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)
from config import *
import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv
from google import genai


# ==========================
# LOAD ENVIRONMENT
# ==========================

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ==========================
# BUSINESS DETAILS
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
# CREATE SLUG
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
# LOAD PROMPT TEMPLATE
# ==========================

prompt_path = Path(
    "04-emails/email-prompt.md"
)

with open(
    prompt_path,
    "r",
    encoding="utf-8"
) as file:

    prompt = file.read()


prompt = prompt.format(
    business_name=business_name,
    business_type=business_type,
    location=location,
    demo_url=demo_url
)


# ==========================
# GENERATE EMAIL
# ==========================

try:

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

except Exception as e:

    print("\n❌ Gemini Error:")
    print(e)

    sys.exit(1)


email = response.text.strip()


# ==========================
# REMOVE MARKDOWN
# ==========================

if email.startswith("```text"):

    email = email.replace(
        "```text",
        ""
    )

email = email.replace(
    "```",
    ""
)

email = email.strip()


# ==========================
# SAVE EMAIL
# ==========================

output_dir = Path(
    "04-emails/generated"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True
)


output_file = (
    output_dir /
    f"{slug}.txt"
)


with open(
    output_file,
    "w",
    encoding="utf-8"
) as file:

    file.write(email)


# ==========================
# SUCCESS
# ==========================

print(
    "\n==============================="
)

print(
    "✅ Email Generated Successfully!"
)

print(
    "==============================="
)

print(
    f"Saved to : {output_file}"
)

print(
    "\n----------- EMAIL -----------\n"
)

print(email)