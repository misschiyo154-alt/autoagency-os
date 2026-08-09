from config import *
import csv
import subprocess
import sys
import re
import time
import os
from datetime import datetime

python = sys.executable

LEADS_FILE = "05-leads/leads.csv"
REDIRECTS_FILE = "_redirects"

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
# SAVE LEADS SAFELY
# ==========================

def save_leads(leads):

    fieldnames = [
        "Business Name",
        "Business Type",
        "Location",
        "Email",
        "Website",
        "Demo URL",
        "Status"
    ]

    if not leads:
        print("⚠️ No leads to save. CSV was NOT changed.")
        return False

    temp_file = LEADS_FILE + ".tmp"

    try:

        with open(
            temp_file,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
                extrasaction="ignore"
            )

            writer.writeheader()
            writer.writerows(leads)

        os.replace(
            temp_file,
            LEADS_FILE
        )

        return True

    except Exception as e:

        print(
            f"❌ Failed to save leads: {e}"
        )

        if os.path.exists(temp_file):

            os.remove(temp_file)

        return False


# ==========================
# UPDATE CLOUDFLARE ROUTES
# ==========================

def update_redirects(slugs):

    existing_routes = []

    if os.path.exists(REDIRECTS_FILE):

        with open(
            REDIRECTS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            existing_routes = [
                line.strip()
                for line in file
                if line.strip()
            ]

    route_map = {}

    # Preserve existing routes
    for route in existing_routes:

        parts = route.split()

        if len(parts) >= 3:

            route_map[parts[0]] = route

    # Add/update current routes
    for slug in slugs:

        route = (
            f"/{slug}/ "
            f"/{slug}/index.html 200"
        )

        route_map[
            f"/{slug}/"
        ] = route

    routes = sorted(
        route_map.values()
    )

    with open(
        REDIRECTS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        for route in routes:

            file.write(
                route + "\n"
            )

    print(
        "\n✅ Cloudflare Routes Updated"
    )

    for route in routes:

        print(route)


# ==========================
# RETRY SUBPROCESS
# ==========================

def run_with_retry(
    command,
    label,
    retries=3
):

    for attempt in range(
        1,
        retries + 1
    ):

        print(
            f"  🔄 {label} "
            f"(attempt {attempt}/{retries})"
        )

        result = subprocess.run(
            command
        )

        if result.returncode == 0:

            return True

        if attempt < retries:

            wait_time = 15 * attempt

            print(
                f"  ⚠️ {label} failed."
            )

            print(
                f"  ⏳ Waiting {wait_time}s "
                f"before retry..."
            )

            time.sleep(
                wait_time
            )

    return False


# ==========================
# LOAD LEADS
# ==========================

with open(
    LEADS_FILE,
    newline="",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(
        file
    )

    leads = list(reader)


# ==========================
# SAFETY CHECK
# ==========================

if not leads:

    print(
        "❌ leads.csv contains no leads."
    )

    print(
        "❌ Nothing was processed."
    )

    sys.exit(1)


# ==========================
# EXISTING SLUGS
# ==========================

slugs = []

for lead in leads:

    status = (
        lead.get("Status") or ""
    ).strip().upper()

    if status == "SUCCESS":

        business_name = (
            lead.get("Business Name") or ""
        ).strip()

        if business_name:

            slug = create_slug(
                business_name
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

    business_name = (
        lead.get("Business Name") or ""
    ).strip()

    business_type = (
        lead.get("Business Type") or ""
    ).strip()

    location = (
        lead.get("Location") or ""
    ).strip()

    status = (
        lead.get("Status") or ""
    ).strip().upper()


    # ==========================
    # VALIDATE LEAD
    # ==========================

    if not business_name:

        print(
            f"\n[{index}/{len(leads)}] "
            f"⚠️ Invalid lead - missing Business Name"
        )

        continue


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

    lead["Demo URL"] = demo_url


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

        lead["Status"] = (
            "WEBSITE_FAILED"
        )

        save_leads(
            leads
        )

        continue


    print(
        "✅ Website Generated"
    )

    lead["Status"] = (
        "WEBSITE_DONE"
    )

    save_leads(
        leads
    )

    slugs.append(
        slug
    )


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

        lead["Status"] = (
            "EMAIL_FAILED"
        )

        save_leads(
            leads
        )

        continue


    print(
        "✅ Email Generated"
    )

    lead["Status"] = (
        "EMAIL_READY"
    )

    save_leads(
        leads
    )


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

    save_leads(
        leads
    )

    successful_leads.append(
        business_name
    )

    print(
        "✅ Lead Completed Successfully"
    )


    # ==========================
    # DELAY
    # ==========================

    print(
        "⏳ Waiting 5 seconds "
        "before next lead..."
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