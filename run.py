from config import *
import csv
import subprocess
import sys
from datetime import datetime

python = sys.executable

print("🚀 Starting AI Agency...\n")

DEMO_URL = "DEMO_URL"

with open("05-leads/leads.csv", newline="", encoding="utf-8") as file:

    reader = csv.DictReader(file)

    for lead in reader:

        business_name = lead["Business Name"]
        business_type = lead["Business Type"]
        location = lead["Location"]

        print("\n====================================")
        print(f"Business : {business_name}")
        print(f"Type     : {business_type}")
        print(f"Location : {location}")
        print("====================================\n")

        # -------------------------
        # Website
        # -------------------------

        result = subprocess.run([
            python,
            "08-scripts/generate_website.py",
            business_name,
            business_type,
            location
        ])

        if result.returncode != 0:
            print("❌ Website Failed")
            continue

        print("✅ Website Generated")

        # -------------------------
        # Email
        # -------------------------

        result = subprocess.run([
            python,
            "04-emails/generate_email.py",
            business_name,
            business_type,
            location,
            DEMO_URL
        ])

        if result.returncode != 0:
            print("❌ Email Failed")
            continue

        print("✅ Email Generated")

        # -------------------------
        # Git Push
        # -------------------------

        result = subprocess.run([
            python,
            "08-scripts/git_push.py"
        ])

        if result.returncode != 0:
            print("❌ Git Push Failed")
            continue

        print("✅ GitHub Updated")

        # -------------------------
        # History
        # -------------------------

        with open(
            "09-history/history.csv",
            "a",
            newline="",
            encoding="utf-8"
        ) as history:

            writer = csv.writer(history)

            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                business_name,
                business_type,
                location,
                "SUCCESS"
            ])

print("\n====================================")
print("🎉 ALL LEADS COMPLETED")
print("====================================")