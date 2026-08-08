from config import *
import csv
import subprocess
import sys
import re
from datetime import datetime

python = sys.executable

print("🚀 Starting AI Agency...\n")


# ==========================
# CREATE SLUG
# ==========================

def create_slug(business_name):

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

    return slug


# ==========================
# UPDATE CLOUDFLARE ROUTES
# ==========================

def update_redirects(slug):

    redirects_file = "_redirects"

    route = (
        f"/{slug}/ "
        f"/{slug}/index.html 200"
    )

    existing_routes = []

    try:

        with open(
            redirects_file,
            "r",
            encoding="utf-8"
        ) as file:

            existing_routes = [
                line.strip()
                for line in file
                if line.strip()
            ]

    except FileNotFoundError:

        pass

    if route not in existing_routes:

        existing_routes.append(route)

    with open(
        redirects_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(existing_routes)
        )

        file.write("\n")


# ==========================
# LOAD LEADS
# ==========================

with open(
    "05-leads/leads.csv",
    newline="",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    for lead in reader:

        business_name = lead["Business Name"]
        business_type = lead["Business Type"]
        location = lead["Location"]

        slug = create_slug(
            business_name
        )

        demo_url = (
            f"{DEMO_URL.rstrip('/')}/"
            f"{slug}/"
        )

        print(
            "\n===================================="
        )

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
            f"Demo URL : {demo_url}"
        )

        print(
            "====================================\n"
        )

        # ==========================
        # Website
        # ==========================

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

        # ==========================
        # Add Cloudflare Route
        # ==========================

        update_redirects(
            slug
        )

        print(
            "✅ Demo Route Added"
        )

        # ==========================
        # Email
        # ==========================

        result = subprocess.run([
            python,
            "04-emails/generate_email.py",
            business_name,
            business_type,
            location,
            demo_url
        ])

        if result.returncode != 0:

            print("❌ Email Failed")

            continue

        print("✅ Email Generated")

        # ==========================
        # Git Push
        # ==========================

        result = subprocess.run([
            python,
            "08-scripts/git_push.py"
        ])

        if result.returncode != 0:

            print("❌ Git Push Failed")

            continue

        print("✅ GitHub Updated")

        # ==========================
        # History
        # ==========================

        with open(
            "09-history/history.csv",
            "a",
            newline="",
            encoding="utf-8"
        ) as history:

            writer = csv.writer(history)

            writer.writerow([
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                ),
                business_name,
                business_type,
                location,
                "SUCCESS"
            ])


print(
    "\n===================================="
)

print(
    "🎉 ALL LEADS COMPLETED"
)

print(
    "===================================="
)