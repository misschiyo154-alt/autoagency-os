import subprocess
import sys
import csv
from datetime import datetime

python = sys.executable

print("🚀 Starting AI Agency...\n")

# -------------------------
# Business Details
# -------------------------
business_name = input("Business Name: ")
business_type = input("Business Type: ")
location = input("Location: ")

# -------------------------
# Generate Website
# -------------------------
result = subprocess.run([
    python,
    "08-scripts/generate_website.py",
    business_name,
    business_type,
    location
])

if result.returncode != 0:
    print("\n❌ Website Generation Failed!")
    exit()

if result.returncode != 0:
    print("\n❌ Website Generation Failed!")
    sys.exit(1)

print("✅ Website Generated")
# -------------------------
# Generate Email
# -------------------------
demo_url = "https://autoagency-os.pages.dev"

result = subprocess.run([
    python,
    "04-emails/generate_email.py",
    business_name,
    business_type,
    location,
    demo_url
])

if result.returncode != 0:
    print("\n❌ Email Generation Failed!")
    exit()

if result.returncode != 0:
    print("\n❌ Email Generation Failed!")
    sys.exit(1)

print("✅ Email Generated")

# -------------------------
# Git Push
# -------------------------
result = subprocess.run([python, "08-scripts/git_push.py"])

if result.returncode != 0:
    print("\n❌ Git Push Failed!")
    exit()

if result.returncode != 0:
    print("\n❌ Email Generation Failed!")
    sys.exit(1)

print("✅ Email Generated")

# -------------------------
# Save History
# -------------------------
with open(
    "09-history/history.csv",
    "a",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.writer(file)

    writer.writerow([
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        business_name,
        business_type,
        location,
        "SUCCESS"
    ])

print("\n====================================")
print("✅ AI Agency Finished Successfully!")
print("====================================")
print(f"Business : {business_name}")
print(f"Location : {location}")
print("Status   : SUCCESS")