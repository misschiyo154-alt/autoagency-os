from config import *
import csv
import subprocess
import sys
import re
import time
from datetime import datetime

python = sys.executable

LEADS_FILE = "05-leads/leads.csv"

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
# SAVE LEADS
# ==========================

def save_leads(leads):

    fieldnames = [
        "Business Name",
        "Business Type",
        "Location",
        "Email",
        "Website",
        "Status"
    ]

    with open(
        LEADS_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(leads)


# ==========================
# UPDATE CLOUDFLARE ROUTES
# ==========================

def update_redirects(slugs):

    redirects_file = "_redirects"

    routes = []

    for slug in sorted(set(slugs)):

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
# RETRY SUBPROCESS
# ==========================

def run_with_retry(command, label, retries=3):

    for attempt in range(1, retries + 1):

        print(
            f"  🔄 {label} "
            f"(attempt {attempt}/{retries})"
        )

        result = subprocess.run(command)

        if result.returncode == 0:

            return True

        if attempt < retries:

            wait_time = 15 * attempt

            print(
                f"  ⚠️ {label} failed."
            )

            print(
                f"  ⏳ Waiting {wait_time}s before retry..."
            )

            time.sleep(wait_time)

    return False


# ==========================
# LOAD LEADS
# ==========================

with open(
    LEADS_FILE,
    newline="",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    leads = list(reader)


# ==========================
# EXISTING SLUGS
# ==========================

slugs = []

for lead in leads:

    status = (
        lead.get("Status") or ""
    ).strip().upper()

    if status == "SUCCESS":

        slug = create_slug(
            lead["Business Name"]
        )

        slugs.append(slug)


# ==========================
# PROCESS LEADS
# ==========================

successful_leads = []

for index, lead in enumerate(
    leads,
    start=1
):

    business_name = lead["Business Name"]
    business_type = lead["Business Type"]
    location = lead["Location"]

    status = (
        lead.get("Status") or ""
    ).strip().upper()


    # ==========================
    # SKIP COMPLETED
    # ==========================

    if status == "SUCCESS":

        print(
            f"\n[{index}/{len(leads)}] "
            f"⏭️ Already completed: "
            f"{business_name}"
        )

        successful_leads.append(
            business_name
        )

        continue


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

    website_success = run_with_retry(
        [
            python,
            "08-scripts/generate_website.py",
            business_name,
            business_type,
            location
        ],
        "Website Generation"
    )

    if not website_success:

        print(
            "❌ Website Failed"
        )

        lead["Status"] = "WEBSITE_FAILED"

        save_leads(leads)

        continue


    print(
        "✅ Website Generated"
    )

    lead["Status"] = "WEBSITE_DONE"

    save_leads(leads)

    slugs.append(slug)


    # ==========================
    # EMAIL
    # ==========================

    email_success = run_with_retry(
        [
            python,
            "04-emails/generate_email.py",
            business_name,
            business_type,
            location,
            demo_url
        ],
        "Email Generation"
    )

    if not email_success:

        print(
            "❌ Email Failed"
        )

        lead["Status"] = "EMAIL_FAILED"

        save_leads(leads)

        continue


    print(
        "✅ Email Generated"
    )

    lead["Status"] = "EMAIL_READY"

    save_leads(leads)


    # ==========================
    # HISTORY
    # ==========================

    with open(
        "09-history/history.csv",
        "a",
        newline="",
        encoding="utf-8"
    ) as history:

        writer = csv.writer(
            history
        )

        writer.writerow([
            datetime.now().strftime(
                "%Y-%m-%d %H:%M"
            ),
            business_name,
            business_type,
            location,
            "SUCCESS"
        ])


    # ==========================
    # FINAL SUCCESS
    # ==========================

    lead["Status"] = "SUCCESS"

    save_leads(leads)

    successful_leads.append(
        business_name
    )

    print(
        "✅ Lead Completed Successfully"
    )


    # Small delay between leads

    print(
        "⏳ Waiting 5 seconds before next lead..."
    )

    time.sleep(5)


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
    f"Successful : "
    f"{len(successful_leads)}"
)

print(
    f"Total      : "
    f"{len(leads)}"
)

print(
    "===================================="
)