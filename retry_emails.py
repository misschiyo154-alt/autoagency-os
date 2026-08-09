import csv
import subprocess
import sys
import os

python = sys.executable

LEADS_FILE = "05-leads/leads.csv"

FIELDNAMES = [
    "Business Name",
    "Business Type",
    "Location",
    "Email",
    "Website",
    "Demo URL",
    "Status"
]

print("📧 Starting Email Retry System...\n")


# ==========================
# LOAD LEADS
# ==========================

with open(
    LEADS_FILE,
    "r",
    newline="",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    leads = list(reader)


if not leads:

    print("❌ No leads found.")
    sys.exit(1)


# ==========================
# NORMALIZE
# ==========================

for lead in leads:

    for field in FIELDNAMES:

        if field not in lead:
            lead[field] = ""

        if lead[field] is None:
            lead[field] = ""


# ==========================
# SAVE
# ==========================

def save_leads():

    temp_file = LEADS_FILE + ".tmp"

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
        writer.writerows(leads)

    os.replace(
        temp_file,
        LEADS_FILE
    )


# ==========================
# PROCESS
# ==========================

ready = 0
sent = 0
failed = 0

for index, lead in enumerate(
    leads,
    start=1
):

    business_name = (
        lead.get("Business Name") or ""
    ).strip()

    email = (
        lead.get("Email") or ""
    ).strip()

    status = (
        lead.get("Status") or ""
    ).strip().upper()


    # ==========================
    # ONLY EMAIL READY / FAILED
    # ==========================

    if status not in [
        "EMAIL_READY",
        "EMAIL_FAILED"
    ]:

        continue


    ready += 1


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
        f"Email    : {email}"
    )

    print(
        f"Status   : {status}"
    )

    print(
        "===================================="
    )


    # ==========================
    # NO EMAIL
    # ==========================

    if not email:

        print(
            "⚠️ No email address. Skipping."
        )

        lead["Status"] = "NO_EMAIL"

        save_leads()

        continue


    # ==========================
    # SEND
    # ==========================

    result = subprocess.run([
        python,
        "04-emails/send_email.py"
    ])


    if result.returncode == 0:

        lead["Status"] = "SENT"

        sent += 1

        print(
            f"✅ {business_name} → SENT"
        )

    else:

        lead["Status"] = "EMAIL_FAILED"

        failed += 1

        print(
            f"❌ {business_name} → EMAIL_FAILED"
        )


    save_leads()


# ==========================
# FINAL SAVE
# ==========================

save_leads()


# ==========================
# FINAL
# ==========================

print(
    "\n===================================="
)

print(
    "📧 EMAIL RETRY COMPLETED"
)

print(
    f"Ready   : {ready}"
)

print(
    f"Sent    : {sent}"
)

print(
    f"Failed  : {failed}"
)

print(
    "===================================="
)