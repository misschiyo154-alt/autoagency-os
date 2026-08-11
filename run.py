from config import *

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from telegram_notify import send_telegram


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

LEADS_FILE = BASE_DIR / "05-leads" / "leads.csv"
BACKUP_FILE = BASE_DIR / "05-leads" / "leads_backup.csv"

HISTORY_FILE = BASE_DIR / "09-history" / "history.csv"

SCRAPER_FILE = BASE_DIR / "08-scripts" / "scrape_leads.py"
ENRICH_FILE = BASE_DIR / "08-scripts" / "enrich_leads.py"

WEBSITE_FILE = (
    BASE_DIR /
    "08-scripts" /
    "generate_website.py"
)

EMAIL_FILE = (
    BASE_DIR /
    "04-emails" /
    "generate_email.py"
)

GIT_FILE = (
    BASE_DIR /
    "08-scripts" /
    "git_push.py"
)

REDIRECTS_FILE = BASE_DIR / "_redirects"


PYTHON = sys.executable


FIELDNAMES = [
    "Business Name",
    "Business Type",
    "Location",
    "Email",
    "Website",
    "Demo URL",
    "Status",
]


# ============================================================
# SETTINGS
# ============================================================

MAX_RETRIES = 3
RETRY_DELAY = 15

DEFAULT_TIMEOUT = 60 * 60


# ============================================================
# START
# ============================================================

print()
print("=" * 60)
print("🚀 AutoAgencyOS Pipeline")
print("=" * 60)


# ============================================================
# ARGUMENTS
# ============================================================

parser = argparse.ArgumentParser(
    description="AutoAgencyOS Lead Pipeline"
)

parser.add_argument(
    "--type",
    dest="business_type",
    required=True,
    help="Business type, e.g. doctors"
)

parser.add_argument(
    "--location",
    dest="location",
    required=True,
    help="Location, e.g. bhilai"
)

parser.add_argument(
    "--quantity",
    dest="quantity",
    type=int,
    required=True,
    help="Number of leads required"
)

args = parser.parse_args()


BUSINESS_TYPE = (
    args.business_type
    .strip()
    .lower()
)

LOCATION = (
    args.location
    .strip()
    .lower()
)

QUANTITY = args.quantity


if QUANTITY <= 0:

    print(
        "❌ Quantity must be greater than 0."
    )

    sys.exit(1)


print(
    f"🎯 Requested leads : {QUANTITY}"
)

print(
    f"🏢 Business type   : {BUSINESS_TYPE}"
)

print(
    f"📍 Location        : {LOCATION}"
)


# ============================================================
# TELEGRAM
# ============================================================

def notify_telegram(message):

    try:

        send_telegram(message)

        print(
            "  📲 Telegram notification sent."
        )

    except Exception as e:

        print(
            f"  ⚠️ Telegram notification failed: {e}"
        )


# ============================================================
# BACKUP
# ============================================================

def create_backup():

    if not LEADS_FILE.exists():

        return

    try:

        shutil.copy2(
            LEADS_FILE,
            BACKUP_FILE
        )

        print(
            "  💾 Leads backup created."
        )

    except Exception as e:

        print(
            f"  ⚠️ Backup failed: {e}"
        )


create_backup()


# ============================================================
# RUN SUBPROCESS
# ============================================================

def run_with_retry(
    command,
    label,
    input_text=None,
    retries=MAX_RETRIES,
    timeout=DEFAULT_TIMEOUT
):

    # Force UTF-8 for all child Python processes.
    # This fixes Windows cp1252 UnicodeEncodeError.
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    for attempt in range(
        1,
        retries + 1
    ):

        print()
        print(
            f"  🔄 {label} "
            f"(attempt {attempt}/{retries})"
        )

        try:

            result = subprocess.run(
                command,
                input=input_text,
                text=True,
                capture_output=True,
                cwd=str(BASE_DIR),
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                env=env
            )

            stdout = (
                result.stdout
                or ""
            )

            stderr = (
                result.stderr
                or ""
            )

            output = stdout

            if stderr:

                output += (
                    "\n"
                    + stderr
                )

            if output.strip():

                print(
                    output.rstrip()
                )

            if result.returncode == 0:

                print(
                    f"  ✅ {label} completed."
                )

                return True

            print(
                f"  ❌ {label} failed "
                f"(exit code {result.returncode})."
            )

        except subprocess.TimeoutExpired:

            print(
                f"  ❌ {label} timed out."
            )

        except Exception as e:

            print(
                f"  ❌ {label} error: {e}"
            )

        if attempt < retries:

            wait_time = (
                RETRY_DELAY * attempt
            )

            print(
                f"  ⏳ Retrying in "
                f"{wait_time}s..."
            )

            time.sleep(
                wait_time
            )

    return False

# ============================================================
# CSV HELPERS
# ============================================================

def read_leads():

    if not LEADS_FILE.exists():

        return []

    try:

        with open(
            LEADS_FILE,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(
                file
            )

            return list(reader)

    except Exception as e:

        print(
            f"❌ Failed reading leads.csv: {e}"
        )

        return []


def save_leads(leads):

    if not leads:

        print(
            "⚠️ No leads to save."
        )

        return False

    temp_file = (
        str(LEADS_FILE)
        + ".tmp"
    )

    try:

        LEADS_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

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
            f"❌ Failed saving leads: {e}"
        )

        if os.path.exists(
            temp_file
        ):

            try:
                os.remove(temp_file)
            except Exception:
                pass

        return False


# ============================================================
# CREATE SLUG
# ============================================================

def create_slug(
    business_name
):

    slug = (
        business_name
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

    return slug.strip("-")


# ============================================================
# REDIRECTS
# ============================================================

def update_redirects(leads):

    slugs = set()

    for lead in leads:

        business_name = (
            lead.get(
                "Business Name"
            )
            or ""
        ).strip()

        if not business_name:

            continue

        slug = create_slug(
            business_name
        )

        if slug:

            slugs.add(slug)

    if not slugs:

        return

    existing_routes = []

    if REDIRECTS_FILE.exists():

        try:

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

        except Exception as e:

            print(
                f"⚠️ Could not read _redirects: {e}"
            )

    route_map = {}

    for route in existing_routes:

        parts = route.split()

        if len(parts) >= 3:

            route_map[
                parts[0]
            ] = route

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

    try:

        with open(
            REDIRECTS_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            for route in routes:

                file.write(
                    route + "\n"
                )

        print()
        print(
            "✅ Cloudflare Routes Updated"
        )

        for route in routes:

            print(
                f"  {route}"
            )

    except Exception as e:

        print(
            f"⚠️ Redirect update failed: {e}"
        )


# ============================================================
# STATUS NORMALIZATION
# ============================================================

def normalize_lead(
    lead
):

    normalized = {}

    for field in FIELDNAMES:

        value = (
            lead.get(field)
            or ""
        )

        normalized[field] = str(
            value
        ).strip()

    return normalized


# ============================================================
# STEP 1
# LEAD DISCOVERY
# ============================================================

print()
print("=" * 60)
print("1️⃣ Lead Discovery")
print("=" * 60)


if not SCRAPER_FILE.exists():

    print(
        f"❌ Scraper missing:\n"
        f"{SCRAPER_FILE}"
    )

    sys.exit(1)


# IMPORTANT:
# scrape_leads.py currently uses:
#
# business_type = input("Business Type: ")
# location = input("Location: ")
#
# Therefore run.py MUST feed those values
# through stdin.

scraper_input = (
    f"{BUSINESS_TYPE}\n"
    f"{LOCATION}\n"
)


scraper_success = run_with_retry(
    [
        PYTHON,
        str(SCRAPER_FILE)
    ],
    "Lead Scraping",
    input_text=scraper_input
)


if not scraper_success:

    print(
        "\n❌ Lead scraping failed."
    )

    sys.exit(1)


# ============================================================
# STEP 2
# LEAD ENRICHMENT
# ============================================================

print()
print("=" * 60)
print("2️⃣ Lead Enrichment")
print("=" * 60)


if not ENRICH_FILE.exists():

    print(
        f"❌ Enrichment script missing:\n"
        f"{ENRICH_FILE}"
    )

    sys.exit(1)


enrich_success = run_with_retry(
    [
        PYTHON,
        str(ENRICH_FILE)
    ],
    "Lead Enrichment"
)


if not enrich_success:

    print(
        "\n❌ Lead enrichment failed."
    )

    sys.exit(1)


# ============================================================
# LOAD SCRAPED + ENRICHED LEADS
# ============================================================

all_leads = read_leads()


if not all_leads:

    print()
    print(
        "❌ leads.csv is empty."
    )

    print(
        "❌ Pipeline stopped safely."
    )

    notify_telegram(
        f"❌ AOS Pipeline Failed\n\n"
        f"Type: {BUSINESS_TYPE}\n"
        f"Location: {LOCATION}\n"
        f"Reason: leads.csv is empty."
    )

    sys.exit(1)


# Normalize
all_leads = [
    normalize_lead(lead)
    for lead in all_leads
]


# ============================================================
# STEP 3
# SELECT REQUESTED LEADS
# ============================================================

print()
print("=" * 60)
print("3️⃣ Selecting Requested Leads")
print("=" * 60)


# Prefer leads matching requested business type/location.
matching_leads = []

for lead in all_leads:

    lead_type = (
        lead.get(
            "Business Type"
        )
        or ""
    ).strip().lower()

    lead_location = (
        lead.get(
            "Location"
        )
        or ""
    ).strip().lower()

    if (
        lead_type == BUSINESS_TYPE
        and lead_location == LOCATION
    ):

        matching_leads.append(
            lead
        )


# If scraper didn't preserve Business Type,
# fall back to location/name data rather than
# killing the entire pipeline.
if not matching_leads:

    location_matches = []

    for lead in all_leads:

        lead_location = (
            lead.get(
                "Location"
            )
            or ""
        ).strip().lower()

        if lead_location == LOCATION:

            lead[
                "Business Type"
            ] = BUSINESS_TYPE

            location_matches.append(
                lead
            )

    matching_leads = location_matches


if not matching_leads:

    print(
        f"❌ No leads found for "
        f"{BUSINESS_TYPE} in {LOCATION}."
    )

    sys.exit(1)


selected_leads = matching_leads[
    :QUANTITY
]


print(
    f"Available matching leads : "
    f"{len(matching_leads)}"
)

print(
    f"Requested leads           : "
    f"{QUANTITY}"
)

print(
    f"Selected leads            : "
    f"{len(selected_leads)}"
)


if not selected_leads:

    print(
        "❌ Nothing selected."
    )

    sys.exit(1)


for index, lead in enumerate(
    selected_leads,
    start=1
):

    print(
        f"  {index}. "
        f"{lead.get('Business Name', 'Unknown')}"
    )


# ============================================================
# IMPORTANT:
# Keep ONLY selected leads in the working CSV.
#
# This prevents generate_website/email from processing
# every old lead in the file.
# ============================================================

save_leads(
    selected_leads
)


# ============================================================
# STEP 4
# WEBSITE + EMAIL
# ============================================================

print()
print("=" * 60)
print("4️⃣ Website + Email Generation")
print("=" * 60)


completed_count = 0
failed_count = 0
ready_count = 0


for index, lead in enumerate(
    selected_leads,
    start=1
):

    business_name = (
        lead.get(
            "Business Name"
        )
        or ""
    ).strip()

    business_type = (
        lead.get(
            "Business Type"
        )
        or BUSINESS_TYPE
    ).strip()

    location = (
        lead.get(
            "Location"
        )
        or LOCATION
    ).strip()

    status = (
        lead.get(
            "Status"
        )
        or ""
    ).strip().upper()


    if not business_name:

        print(
            f"\n[{index}/{len(selected_leads)}]"
        )

        print(
            "⚠️ Missing Business Name. Skipping."
        )

        failed_count += 1

        continue


    slug = create_slug(
        business_name
    )


    # ========================================================
    # DEMO URL
    # ========================================================

    demo_base = (
        globals().get(
            "DEMO_URL",
            ""
        )
        or ""
    ).strip()

    if demo_base:

        demo_url = (
            demo_base.rstrip("/")
            + "/"
            + slug
            + "/"
        )

    else:

        demo_url = (
            f"/{slug}/"
        )


    lead[
        "Demo URL"
    ] = demo_url


    print()
    print("-" * 60)

    print(
        f"[{index}/{len(selected_leads)}]"
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
        f"Status   : {status or 'NEW'}"
    )

    print(
        f"Demo URL : {demo_url}"
    )

    print(
        "-" * 60
    )


    # ========================================================
    # WEBSITE
    # ========================================================

    if status in [
        "WEBSITE_DONE",
        "EMAIL_READY",
        "EMAIL_FAILED",
        "SUCCESS",
        "SENT"
    ]:

        print(
            "⏭️ Website already completed."
        )

    else:

        website_success = run_with_retry(
            [
                PYTHON,
                str(WEBSITE_FILE),
                business_name,
                business_type,
                location
            ],
            "Website Generation"
        )


        if not website_success:

            print(
                "❌ Website Generation Failed."
            )

            lead[
                "Status"
            ] = "WEBSITE_FAILED"

            save_leads(
                selected_leads
            )

            notify_telegram(
                f"❌ AOS Lead Failed\n\n"
                f"Business: {business_name}\n"
                f"Type: {business_type}\n"
                f"Location: {location}\n\n"
                f"Stage: Website Generation\n"
                f"Status: WEBSITE_FAILED"
            )

            failed_count += 1

            continue


        print(
            "✅ Website Generated."
        )

        lead[
            "Status"
        ] = "WEBSITE_DONE"

        save_leads(
            selected_leads
        )


    # ========================================================
    # EMAIL
    # ========================================================

    current_status = (
        lead.get(
            "Status"
        )
        or ""
    ).strip().upper()


    if current_status == "EMAIL_READY":

        print(
            "⏭️ Email already generated."
        )

        ready_count += 1

        continue


    if current_status == "EMAIL_FAILED":

        print(
            "⏭️ Email previously failed."
        )

        continue


    email_success = run_with_retry(
        [
            PYTHON,
            str(EMAIL_FILE),
            business_name,
            business_type,
            location,
            demo_url
        ],
        "Email Generation"
    )


    if not email_success:

        print(
            "❌ Email Generation Failed."
        )

        lead[
            "Status"
        ] = "EMAIL_FAILED"

        save_leads(
            selected_leads
        )

        notify_telegram(
            f"⚠️ AOS Lead Ready — Email Failed\n\n"
            f"Business: {business_name}\n"
            f"Type: {business_type}\n"
            f"Location: {location}\n\n"
            f"🌐 Demo:\n"
            f"{demo_url}\n\n"
            f"Status: EMAIL_FAILED"
        )

        failed_count += 1

        continue


    print(
        "✅ Email Generated."
    )

    lead[
        "Status"
    ] = "EMAIL_READY"

    save_leads(
        selected_leads
    )

    ready_count += 1


    # ========================================================
    # TELEGRAM
    # ========================================================

    notify_telegram(
        f"🚀 AOS Lead Ready\n\n"
        f"Business: {business_name}\n"
        f"Type: {business_type}\n"
        f"Location: {location}\n\n"
        f"🌐 Demo:\n"
        f"{demo_url}\n\n"
        f"📧 Email: Generated\n"
        f"📌 Status: EMAIL_READY"
    )


    completed_count += 1


# ============================================================
# STEP 5
# UPDATE REDIRECTS
# ============================================================

print()
print("=" * 60)
print("5️⃣ Updating Cloudflare Routes")
print("=" * 60)


update_redirects(
    selected_leads
)


# ============================================================
# FINAL CSV
# ============================================================

save_leads(
    selected_leads
)


# ============================================================
# STEP 6
# GIT PUSH
# ============================================================

print()
print("=" * 60)
print("6️⃣ GitHub Update")
print("=" * 60)


if GIT_FILE.exists():

    git_result = subprocess.run(
        [
            PYTHON,
            str(GIT_FILE)
        ],
        cwd=str(BASE_DIR)
    )


    if git_result.returncode == 0:

        print(
            "✅ GitHub Updated Successfully."
        )

    else:

        print(
            "❌ Git Push Failed."
        )

else:

    print(
        "⚠️ git_push.py not found. Skipping."
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 60)
print("🎉 PIPELINE COMPLETED")
print("=" * 60)

print(
    f"Requested : {QUANTITY}"
)

print(
    f"Selected  : {len(selected_leads)}"
)

print(
    f"Ready     : {ready_count}"
)

print(
    f"Failed    : {failed_count}"
)

print(
    f"Total CSV : {len(selected_leads)}"
)

print(
    "=" * 60
)


# ============================================================
# TELEGRAM SUMMARY
# ============================================================

notify_telegram(
    f"🏁 AOS Pipeline Completed\n\n"
    f"🏢 Type: {BUSINESS_TYPE}\n"
    f"📍 Location: {LOCATION}\n\n"
    f"🎯 Requested: {QUANTITY}\n"
    f"📌 Selected: {len(selected_leads)}\n"
    f"📧 Email Ready: {ready_count}\n"
    f"❌ Failed: {failed_count}"
)