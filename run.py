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

    slug = slug.replace("&", "and")

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        slug
    )

    return slug.strip("-")


# ==========================
# UPDATE CLOUDFLARE ROUTES
# ==========================

def update_redirects(slugs):

    redirects_file = "_redirects"

    routes = []

    for slug in slugs:

        route = (
            f"/{slug}/ "
            f"/{slug}/index.html 200"
        )

        routes.append(route)

    with open(
        redirects_file,
        "w",
        encoding="utf-8"
    ) as file:

        for route in routes:
            file.write(route + "\n")

    print("\n✅ Cloudflare Routes Updated")

    for route in routes:
        print(route)


# ==========================
# LOAD LEADS
# ==========================

with open(
    "05-leads/leads.csv",
    newline="",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    leads = list(reader)


# ==========================
# PROCESS LEADS
# ==========================

slugs = []

successful_leads = []

for index, lead in enumerate(
    leads,
    start=1
):

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
        f"[{index}/{len(leads)}]"
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
    # WEBSITE
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
    slugs.append(slug)

    # ==========================
    # EMAIL
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
    # HISTORY
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


    successful_leads.append(
        business_name
    )


# ==========================
# UPDATE REDIRECTS
# ==========================

update_redirects(
    slugs
)


# ==========================
# ONE GIT PUSH
# ==========================

print(
    "\n🚀 Updating GitHub..."
)

result = subprocess.run([
    python,
    "08-scripts/git_push.py"
])

if result.returncode != 0:

    print(
        "\n❌ Git Push Failed"
    )

else:

    print(
        "\n✅ GitHub Updated Successfully"
    )


# ==========================
# FINAL
# ==========================

print(
    "\n===================================="
)

print(
    "🎉 ALL LEADS COMPLETED"
)

print(
    f"Successful : {len(successful_leads)}"
)

print(
    f"Total      : {len(leads)}"
)

print(
    "===================================="
)