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
HISTORY_FILE = "09-history/history.csv"

FIELDNAMES = [
    "Business Name",
    "Business Type",
    "Location",
    "Email",
    "Website",
    "Demo URL",
    "Status"
]

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

    return slug.strip("-")


# ==========================
# SAVE LEADS SAFELY
# ==========================

def save_leads(leads):

    if not leads:

        print(
            "⚠️ No leads to save. "
            "CSV was NOT changed."
        )

        return False

    temp_file = (
        LEADS_FILE + ".tmp"
    )

    try:

        with open(
            temp_file,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=FIELDNAMES,
                extrasaction="ignore"
            )

            writer.writeheader()

            writer.writerows(
                leads
            )

        os.replace(
            temp_file,
            LEADS_FILE
        )

        return True

    except Exception as e:

        print(
            f"❌ Failed to save leads: {e}"
        )

        if os.path.exists(
            temp_file
        ):

            os.remove(
                temp_file
            )

        return False


# ==========================
# UPDATE CLOUDFLARE ROUTES
# ==========================

def update_redirects(slugs):

    existing_routes = []

    if os.path.exists(
        REDIRECTS_FILE
    ):

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

            route_map[
                parts[0]
            ] = route

    # Add current routes
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

            wait_time = (
                15 * attempt
            )

            print(
                f"  ⚠️ {label} failed."
            )

            print(
                f"  ⏳ Waiting "
                f"{wait_time}s "
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

    sys.exit(1)


# ==========================
# NORMALIZE LEADS
# ==========================

for lead in leads:

    for field in FIELDNAMES:

        if field not in lead:

            lead[field] = ""

        elif lead[field] is None:

            lead[field] = ""


# ==========================
# EXISTING SLUGS
# ==========================

slugs = []

for lead in leads:

    business_name = (
        lead.get("Business Name") or ""
    ).strip()

    if not business_name:

        continue

    status = (
        lead.get("Status") or ""
    ).strip().upper()

    demo_url = (
        lead.get("Demo URL") or ""
    ).strip()

    slug = create_slug(
        business_name
    )

    # Existing completed/generated
    if status in [
        "SUCCESS",
        "SENT",
        "EMAIL_READY",
        "EMAIL_FAILED",
        "WEBSITE_DONE",
        "WEBSITE_FAILED"
    ]:

        slugs.append(
            slug
        )

    # If Demo URL already exists,
    # preserve route too.
    if demo_url:

        slugs.append(
            slug
        )


# ==========================
# PROCESS LEADS
# ==========================

completed_count = 0

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
    # VALIDATE
    # ==========================

    if not business_name:

        print(
            f"\n[{index}/{len(leads)}] "
            "⚠️ Missing Business Name"
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

    slugs.append(
        slug
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
        f"Status   : {status or 'NEW'}"
    )

    print(
        f"Demo URL : {demo_url}"
    )

    print(
        "===================================="
    )


    # ==================================================
    # 1. FULLY COMPLETED
    # ==================================================

    if status in [
        "SUCCESS",
        "SENT"
    ]:

        print(
            "⏭️ Already completed."
        )

        completed_count += 1

        continue


    # ==================================================
    # 2. WEBSITE ALREADY DONE
    # ==================================================
    #
    # IMPORTANT:
    # WEBSITE_DONE
    # EMAIL_FAILED
    # EMAIL_READY
    #
    # will NEVER regenerate website.
    # ==================================================

    if status in [
        "WEBSITE_DONE",
        "EMAIL_FAILED",
        "EMAIL_READY"
    ]:

        print(
            "⏭️ Website already exists."
        )

    else:

        # ==========================
        # WEBSITE GENERATION
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


    # ==================================================
    # 3. EMAIL ALREADY READY
    # ==================================================

    current_status = (
        lead.get("Status") or ""
    ).strip().upper()


    if current_status == "EMAIL_READY":

        print(
            "⏭️ Email already generated."
        )

        continue


    # ==================================================
    # 4. EMAIL GENERATION
    # ==================================================

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
            "❌ Email Generation Failed"
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


    print(
        "📌 Lead is now EMAIL_READY."
    )

    print(
        "📧 Use retry_emails.py "
        "to send it."
    )


# ==========================
# UPDATE REDIRECTS
# ==========================

update_redirects(
    slugs
)


# ==========================
# SAVE FINAL CSV
# ==========================

save_leads(
    leads
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
    "🎉 PIPELINE COMPLETED"
)

print(
    f"Completed/Existing : "
    f"{completed_count}"
)

print(
    f"Total Leads        : "
    f"{len(leads)}"
)

print(
    "===================================="
)