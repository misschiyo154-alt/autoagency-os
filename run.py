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
result = subprocess.run(
    [python, "08-scripts/generate_website.py"],
    input=f"{business_name}\n{business_type}\n{location}\n",
    text=True
)

if result.returncode != 0:
    print("\n❌ Website Generation Failed!")
    exit()

# -------------------------
# Generate Email
# -------------------------
demo_url = input("Demo Website URL: ")

result = subprocess.run(
    [python, "04-emails/generate_email.py"],
    input=f"{business_name}\n{business_type}\n{location}\n{demo_url}\n",
    text=True
)

if result.returncode != 0:
    print("\n❌ Email Generation Failed!")
    exit()

# -------------------------
# Git Push
# -------------------------
result = subprocess.run([python, "08-scripts/git_push.py"])

if result.returncode != 0:
    print("\n❌ Git Push Failed!")
    exit()

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