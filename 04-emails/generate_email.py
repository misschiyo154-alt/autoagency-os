import sys
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv



# ============================================================
# AUTOAGENCYOS EMAIL GENERATOR
# ============================================================

# File is:
# C:\AutoAgencyOS\04-emails\generate_email.py
#
# Therefore:
# parents[0] = 04-emails
# parents[1] = AutoAgencyOS

BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(BASE_DIR))
from config import AGENCY_URL

PROMPT_PATH = BASE_DIR / "04-emails" / "email-prompt.md"
OUTPUT_DIR = BASE_DIR / "04-emails" / "generated"

# Load C:\AutoAgencyOS\.env
load_dotenv(BASE_DIR / ".env")


# ============================================================
# ARGUMENTS
# ============================================================

if len(sys.argv) == 5:
    business_name = sys.argv[1].strip()
    business_type = sys.argv[2].strip()
    location = sys.argv[3].strip()
    demo_url = sys.argv[4].strip()
else:
    business_name = input("Business Name: ").strip()
    business_type = input("Business Type: ").strip()
    location = input("Location: ").strip()
    demo_url = input("Demo Website URL: ").strip()


# ============================================================
# CLEAN DEMO URL
# ============================================================

# Accept:
# https://example.com
#
# Also safely handle:
# [https://example.com](https://example.com)

markdown_match = re.fullmatch(
    r"\[([^\]]+)\]\(([^)]+)\)",
    demo_url
)

if markdown_match:
    demo_url = markdown_match.group(2).strip()


# Remove accidental surrounding quotes
demo_url = demo_url.strip().strip('"').strip("'")


# Ensure URL has protocol
if demo_url and not demo_url.startswith(("http://", "https://")):
    demo_url = "https://" + demo_url


if not demo_url:
    print("\n[ERROR] Demo URL is empty.")
    sys.exit(1)


# ============================================================
# LOAD PROMPT
# ============================================================

if not PROMPT_PATH.exists():
    print("\n[ERROR] Email prompt file not found.")
    print(f"Expected: {PROMPT_PATH}")
    sys.exit(1)


try:
    with open(PROMPT_PATH, "r", encoding="utf-8") as file:
        prompt_template = file.read()

except Exception as e:
    print("\n[ERROR] Could not read email prompt.")
    print(f"Error: {e}")
    sys.exit(1)


# ============================================================
# BUILD PROMPT
# ============================================================

try:
    prompt = prompt_template.format(
        business_name=business_name,
        business_type=business_type,
        location=location,
        demo_url=demo_url
    )

except Exception as e:
    print("\n[ERROR] Could not build email prompt.")
    print(f"Error: {e}")
    sys.exit(1)


# ============================================================
# GROQ CONFIG
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MODEL = "llama-3.3-70b-versatile"


if not GROQ_API_KEY:
    print("\n[ERROR] GROQ_API_KEY not found.")
    print(f"Checked: {BASE_DIR / '.env'}")
    sys.exit(1)


# ============================================================
# DISPLAY
# ============================================================

print()
print("=======================================================")
print("GROQ EMAIL GENERATOR")
print("=======================================================")
print(f"Business : {business_name}")
print(f"Type     : {business_type}")
print(f"Location : {location}")
print(f"Model    : {MODEL}")
print()
print("[AI] Generating personalized email...")


# ============================================================
# GROQ REQUEST
# ============================================================

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": MODEL,
    "messages": [
        {
            "role": "system",
            "content": (
                "You are a professional cold-email copywriter "
                "working for Vicky Web Agency. "
                "Follow the user's instructions exactly. "
                "Return ONLY the finished email. "
                "Do not explain anything."
            )
        },
        {
            "role": "user",
            "content": prompt
        }
    ],
    "temperature": 0.35,
    "max_tokens": 400
}


try:
    response = requests.post(
        GROQ_URL,
        headers=headers,
        json=payload,
        timeout=120
    )

except requests.exceptions.Timeout:
    print("\n[ERROR] Groq API timed out.")
    sys.exit(1)

except requests.exceptions.ConnectionError:
    print("\n[ERROR] Could not connect to Groq.")
    sys.exit(1)

except requests.exceptions.RequestException as e:
    print("\n[ERROR] Groq request failed.")
    print(e)
    sys.exit(1)


# ============================================================
# API ERROR
# ============================================================

if response.status_code != 200:

    print("\n[ERROR] Groq API failed.")
    print(f"Status: {response.status_code}")

    try:
        print(response.json())
    except Exception:
        print(response.text)

    sys.exit(1)


# ============================================================
# READ RESPONSE
# ============================================================

try:
    data = response.json()

    email = data["choices"][0]["message"]["content"].strip()

except Exception as e:

    print("\n[ERROR] Invalid Groq response.")
    print(f"Error: {e}")
    print("\nRaw response:")
    print(response.text)

    sys.exit(1)


if not email:
    print("\n[ERROR] Groq returned empty output.")
    sys.exit(1)


# ============================================================
# CLEAN AI OUTPUT
# ============================================================

# Remove <think>...</think>
email = re.sub(
    r"<think>.*?</think>",
    "",
    email,
    flags=re.DOTALL | re.IGNORECASE
).strip()


# Remove code fences
email = re.sub(
    r"```(?:text|txt|markdown)?",
    "",
    email,
    flags=re.IGNORECASE
)

email = email.replace("```", "").strip()


# Remove accidental AI intro
email = re.sub(
    r"^(Here(?:'s| is)(?: the)?(?: finished)? email:?)\s*",
    "",
    email,
    flags=re.IGNORECASE
).strip()


# Remove trailing separator
email = re.sub(
    r"\n\s*-{3,}\s*$",
    "",
    email
).strip()


# ============================================================
# FORCE EXACT DEMO URL
# ============================================================

# Sometimes the model changes the URL.
# Replace any markdown version of the demo URL
# with the exact normal URL.

email = email.replace(
    f"[{demo_url}]({demo_url})",
    demo_url
)

# If the model somehow used the generic placeholder,
# replace it with the real demo URL.

email = email.replace(
    "https://your-demo-url.com",
    demo_url
)

email = email.replace(
    "http://your-demo-url.com",
    demo_url
)


# ============================================================
# REMOVE COMMON PLACEHOLDERS
# ============================================================

email = email.replace("[Your Name]", "Vicky")
email = email.replace("[Name]", "Vicky")
email = email.replace("[Company]", "Vicky Web Agency")
email = email.replace("[Agency]", "Vicky Web Agency")
email = email.replace("[Your Demo URL]", demo_url)
email = email.replace("[Demo Website]", demo_url)


# ============================================================
# NORMALIZE MARKDOWN URL
# ============================================================

email = email.replace(
    f"[{demo_url}]({demo_url})",
    demo_url
)


# ============================================================
# CHECK REQUIRED CONTENT
# ============================================================

if demo_url not in email:
    print("\n[WARNING] AI did not include the demo URL.")
    print("[FIX] Adding the demo URL automatically.")

    # Add URL after first paragraph if missing.
    lines = email.splitlines()

    insert_at = min(4, len(lines))

    lines.insert(insert_at, demo_url)

    email = "\n".join(lines).strip()


# ============================================================
# REMOVE MARKDOWN
# ============================================================

email = re.sub(
    r"\*\*(.*?)\*\*",
    r"\1",
    email
)

email = re.sub(
    r"\*(.*?)\*",
    r"\1",
    email
)

email = re.sub(
    r"__(.*?)__",
    r"\1",
    email
)

email = email.replace("# ", "")


# ============================================================
# CLEAN WHITESPACE
# ============================================================

email = re.sub(
    r"[ \t]+",
    " ",
    email
)

email = re.sub(
    r"\n{3,}",
    "\n\n",
    email
).strip()


# ============================================================
# REMOVE TRAILING NOTES
# ============================================================

email = re.sub(
    r"\n+(?:Note|Notes|Word count|Explanation|Reasoning):.*$",
    "",
    email,
    flags=re.IGNORECASE | re.DOTALL
).strip()


# ============================================================
# ENSURE SIGNATURE
# ============================================================

# If model produced a different signature, normalize it.

email = re.sub(
    r"\n*(?:Best regards|Best|Regards|Sincerely|Thanks|Thank you),?\s*\n+.*?(?:Vicky Web Agency)?\s*$",
    "",
    email,
    flags=re.IGNORECASE | re.DOTALL
).strip()

email += "\n\nBest,\nVicky\nVicky Web Agency"


# ============================================================
# SAVE
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# Safe filename
slug = business_name.lower()

slug = slug.replace("&", "and")

slug = re.sub(
    r"[^a-z0-9]+",
    "-",
    slug
)

slug = slug.strip("-")


if not slug:
    slug = "business"


output_file = OUTPUT_DIR / f"{slug}.txt"


try:

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(email)

except Exception as e:

    print("\n[ERROR] Could not save email.")
    print(f"Error: {e}")
    sys.exit(1)


# ============================================================
# RESULT
# ============================================================

print()
print("[OK] Email generated successfully.")
print(f"Saved: {output_file}")

print()
print("---------------- EMAIL ----------------")
print()
print(email)
print()
print("----------------------------------------")