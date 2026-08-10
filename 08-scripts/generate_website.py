import os
import sys
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("\n❌ GEMINI_API_KEY missing in .env")
    sys.exit(1)


# ============================================================
# CREATE GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=api_key
)


# ============================================================
# USER INPUTS
# ============================================================

if len(sys.argv) == 4:

    business_name = sys.argv[1]
    business_type = sys.argv[2]
    location = sys.argv[3]

else:

    business_name = input("Business Name: ")
    business_type = input("Business Type: ")
    location = input("Location: ")


# ============================================================
# READ PROMPT
# ============================================================

prompt_path = Path(
    "03-prompts/website-generator.md"
)

try:

    with open(
        prompt_path,
        "r",
        encoding="utf-8"
    ) as file:

        prompt_template = file.read()

except FileNotFoundError:

    print(
        f"\n❌ Prompt file not found: {prompt_path}"
    )

    sys.exit(1)


# ============================================================
# REPLACE VARIABLES
# ============================================================

prompt = prompt_template.format(
    business_name=business_name,
    business_type=business_type,
    location=location
)


# ============================================================
# GENERATE WEBSITE
# ============================================================

print(
    "\n🤖 Generating website with Gemini..."
)

try:

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

except Exception as e:

    print("\n❌ Gemini Error:")
    print(e)

    sys.exit(1)


# ============================================================
# GET HTML
# ============================================================

html = (
    response.text or ""
).strip()

if not html:

    print(
        "\n❌ Gemini returned empty website."
    )

    sys.exit(1)


# ============================================================
# REMOVE MARKDOWN CODE FENCES
# ============================================================

html = re.sub(
    r"^```html\s*",
    "",
    html,
    flags=re.IGNORECASE
)

html = re.sub(
    r"^```\s*",
    "",
    html
)

html = re.sub(
    r"\s*```$",
    "",
    html
).strip()


# ============================================================
# CREATE SAFE SLUG
# ============================================================

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


if not slug:

    print(
        "\n❌ Could not create a valid website slug."
    )

    sys.exit(1)


# ============================================================
# SAVE CLIENT WEBSITE
# ============================================================

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


# ============================================================
# SAVE LATEST GENERATED WEBSITE
# ============================================================

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


# ============================================================
# DEMO URL
# ============================================================

demo_url = (
    f"https://autoagency-os.pages.dev/"
    f"{slug}/"
)


# ============================================================
# RESULT
# ============================================================

print(
    f"\n📁 Website Saved: {output}"
)

print(
    f"🌐 Demo URL: {demo_url}"
)

print(
    "\n✅ Website Generated Successfully!"
)