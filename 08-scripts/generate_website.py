import os
import sys
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# ============================================================
# WINDOWS UTF-8 FIX
# ============================================================

def configure_utf8():
    """
    Force Python stdout/stderr to UTF-8 when possible.
    Prevents Windows CP1252 UnicodeEncodeError.
    """

    try:

        if hasattr(sys.stdout, "reconfigure"):

            sys.stdout.reconfigure(
                encoding="utf-8",
                errors="replace"
            )

        if hasattr(sys.stderr, "reconfigure"):

            sys.stderr.reconfigure(
                encoding="utf-8",
                errors="replace"
            )

    except Exception:
        pass


configure_utf8()


# ============================================================
# PROJECT PATH
# ============================================================

# This file is:
#
# C:\AutoAgencyOS\08-scripts\generate_website.py
#
# parent        = C:\AutoAgencyOS\08-scripts
# parent.parent = C:\AutoAgencyOS
#
# So project root is parent.parent

BASE_DIR = Path(
    __file__
).resolve().parent.parent


# ============================================================
# PROJECT PATHS
# ============================================================

ENV_FILE = (
    BASE_DIR
    / ".env"
)

PROMPT_FILE = (
    BASE_DIR
    / "03-prompts"
    / "website-generator.md"
)

WEBSITES_DIR = (
    BASE_DIR
    / "02-websites"
)

GENERATED_DIR = (
    WEBSITES_DIR
    / "generated"
)


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv(
    ENV_FILE
)


api_key = os.getenv(
    "GEMINI_API_KEY"
)


if not api_key:

    print()
    print(
        "[ERROR] GEMINI_API_KEY missing in .env"
    )

    print(
        f"Expected .env file:"
    )

    print(
        f"{ENV_FILE}"
    )

    print()
    print(
        "Make sure your .env contains:"
    )

    print(
        "GEMINI_API_KEY=your_api_key_here"
    )

    sys.exit(1)


# ============================================================
# CREATE GEMINI CLIENT
# ============================================================

try:

    client = genai.Client(
        api_key=api_key
    )

except Exception as error:

    print()
    print(
        "[ERROR] Could not create Gemini client."
    )

    print(
        error
    )

    sys.exit(1)


# ============================================================
# USER INPUT
# ============================================================

if len(sys.argv) == 4:

    business_name = (
        sys.argv[1]
        .strip()
    )

    business_type = (
        sys.argv[2]
        .strip()
    )

    location = (
        sys.argv[3]
        .strip()
    )

else:

    business_name = input(
        "Business Name: "
    ).strip()

    business_type = input(
        "Business Type: "
    ).strip()

    location = input(
        "Location: "
    ).strip()


# ============================================================
# VALIDATE INPUT
# ============================================================

if not business_name:

    print(
        "[ERROR] Business Name is empty."
    )

    sys.exit(1)


if not business_type:

    print(
        "[ERROR] Business Type is empty."
    )

    sys.exit(1)


if not location:

    print(
        "[ERROR] Location is empty."
    )

    sys.exit(1)


# ============================================================
# HEADER
# ============================================================

print()
print("=" * 60)
print("AutoAgencyOS Website Generator")
print("=" * 60)

print(
    f"Business : {business_name}"
)

print(
    f"Type     : {business_type}"
)

print(
    f"Location : {location}"
)

print(
    f"Project  : {BASE_DIR}"
)

print(
    "=" * 60
)


# ============================================================
# READ PROMPT
# ============================================================

if not PROMPT_FILE.exists():

    print()
    print(
        "[ERROR] Prompt file not found."
    )

    print(
        f"Expected:"
    )

    print(
        f"{PROMPT_FILE}"
    )

    sys.exit(1)


try:

    prompt_template = PROMPT_FILE.read_text(
        encoding="utf-8"
    )

except Exception as error:

    print()
    print(
        "[ERROR] Could not read website prompt."
    )

    print(
        error
    )

    sys.exit(1)


# ============================================================
# REPLACE VARIABLES
# ============================================================

try:

    prompt = prompt_template.format(
        business_name=business_name,
        business_type=business_type,
        location=location
    )

except KeyError as error:

    print()
    print(
        "[ERROR] Unknown variable found in website-generator.md"
    )

    print(
        f"Variable: {error}"
    )

    print()
    print(
        "The prompt should use:"
    )

    print(
        "{business_name}"
    )

    print(
        "{business_type}"
    )

    print(
        "{location}"
    )

    sys.exit(1)

except Exception as error:

    print()
    print(
        "[ERROR] Could not prepare Gemini prompt."
    )

    print(
        error
    )

    sys.exit(1)


# ============================================================
# GENERATE WEBSITE
# ============================================================

print()
print(
    "[AI] Generating website with Gemini..."
)

print(
    "[AI] Please wait..."
)


try:

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

except Exception as error:

    print()
    print(
        "[ERROR] Gemini API request failed."
    )

    print(
        error
    )

    sys.exit(1)


# ============================================================
# GET HTML
# ============================================================

try:

    html = (
        response.text
        or ""
    ).strip()

except Exception:

    html = ""


if not html:

    print()
    print(
        "[ERROR] Gemini returned empty website."
    )

    sys.exit(1)


# ============================================================
# CLEAN MARKDOWN FENCES
# ============================================================

def clean_generated_html(content):

    content = (
        content
        .strip()
    )

    # Remove opening ```html
    content = re.sub(
        r"^\s*```html\s*",
        "",
        content,
        flags=re.IGNORECASE
    )

    # Remove opening ```
    content = re.sub(
        r"^\s*```\s*",
        "",
        content
    )

    # Remove closing ```
    content = re.sub(
        r"\s*```\s*$",
        "",
        content
    )

    return content.strip()


html = clean_generated_html(
    html
)


# ============================================================
# EXTRACT ACTUAL HTML
# ============================================================

lower_html = html.lower()

doctype_position = lower_html.find(
    "<!doctype"
)

html_position = lower_html.find(
    "<html"
)


possible_positions = [
    position
    for position in [
        doctype_position,
        html_position
    ]
    if position >= 0
]


if possible_positions:

    first_html_position = min(
        possible_positions
    )

    if first_html_position > 0:

        html = html[
            first_html_position:
        ]


# ============================================================
# CUT AFTER </html>
# ============================================================

closing_html_position = (
    html.lower().rfind(
        "</html>"
    )
)


if closing_html_position >= 0:

    closing_html_position += len(
        "</html>"
    )

    html = html[
        :closing_html_position
    ]


html = html.strip()


# ============================================================
# VALIDATE HTML
# ============================================================

if len(html) < 100:

    print()
    print(
        "[ERROR] Generated HTML is suspiciously short."
    )

    print(
        f"HTML length: {len(html)}"
    )

    sys.exit(1)


# ============================================================
# CREATE SAFE SLUG
# ============================================================

def create_slug(name):

    slug = (
        name
        .lower()
        .strip()
    )

    slug = slug.replace(
        "&",
        "and"
    )

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        slug
    )

    slug = slug.strip(
        "-"
    )

    return slug


slug = create_slug(
    business_name
)


if not slug:

    print()
    print(
        "[ERROR] Could not create valid website slug."
    )

    sys.exit(1)


# ============================================================
# CREATE CLIENT FOLDER
# ============================================================

client_folder = (
    WEBSITES_DIR
    / slug
)


try:

    client_folder.mkdir(
        parents=True,
        exist_ok=True
    )

except Exception as error:

    print()
    print(
        "[ERROR] Could not create client website folder."
    )

    print(
        error
    )

    sys.exit(1)


# ============================================================
# SAVE CLIENT WEBSITE
# ============================================================

client_output = (
    client_folder
    / "index.html"
)


try:

    client_output.write_text(
        html,
        encoding="utf-8"
    )

except Exception as error:

    print()
    print(
        "[ERROR] Could not save client website."
    )

    print(
        error
    )

    sys.exit(1)


# ============================================================
# SAVE LATEST GENERATED WEBSITE
# ============================================================

latest_output = (
    GENERATED_DIR
    / "index.html"
)


try:

    GENERATED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    latest_output.write_text(
        html,
        encoding="utf-8"
    )

except Exception as error:

    print()
    print(
        "[ERROR] Could not save generated/index.html."
    )

    print(
        error
    )

    sys.exit(1)


# ============================================================
# DEMO URL
# ============================================================

demo_url = (
    "https://autoagency-os.pages.dev/"
    + slug
    + "/"
)


# ============================================================
# RESULT
# ============================================================

print()
print("=" * 60)
print("WEBSITE GENERATED SUCCESSFULLY")
print("=" * 60)

print(
    f"Business : {business_name}"
)

print(
    f"Slug     : {slug}"
)

print(
    f"Saved    : {client_output}"
)

print(
    f"Latest   : {latest_output}"
)

print(
    f"Demo URL : {demo_url}"
)

print(
    "=" * 60
)


# ============================================================
# SUCCESS
# ============================================================

sys.exit(0)