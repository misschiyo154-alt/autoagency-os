import os
import csv
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path
from dotenv import load_dotenv


# ==========================
# LOAD ENV
# ==========================

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")


# ==========================
# FILES
# ==========================

LEADS_FILE = "05-leads/leads.csv"
EMAIL_DIR = Path("04-emails/generated")


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


# ==========================
# FIELDNAMES
# ==========================

fieldnames = [
    "Business Name",
    "Business Type",
    "Location",
    "Email",
    "Website",
    "Demo URL",
    "Status"
]


# ==========================
# FIND FIRST READY LEAD
# ==========================

target_index = None

receiver = None

for index, lead in enumerate(leads):

    email = (
        lead.get("Email") or ""
    ).strip()

    status = (
        lead.get("Status") or ""
    ).strip().upper()

    if (
        email
        and status == "EMAIL_READY"
    ):

        target_index = index

        receiver = email

        break


# ==========================
# NO READY LEAD
# ==========================

if target_index is None:

    print(
        "\n⚠️ No EMAIL_READY leads found."
    )

    raise SystemExit(0)


# ==========================
# BUSINESS
# ==========================

business_name = (
    leads[target_index]
    .get("Business Name") or ""
).strip()


slug = create_slug(
    business_name
)


# ==========================
# EMAIL FILE
# ==========================

email_file = (
    EMAIL_DIR /
    f"{slug}.txt"
)


if not email_file.exists():

    print(
        f"\n❌ Email file not found:"
    )

    print(
        f"   {email_file}"
    )

    raise SystemExit(1)


# ==========================
# READ EMAIL
# ==========================

with open(
    email_file,
    "r",
    encoding="utf-8"
) as file:

    content = file.read().strip()


lines = content.splitlines()

subject = "Website Redesign"

body = content


if (
    lines
    and lines[0]
    .lower()
    .startswith("subject:")
):

    subject = (
        lines[0]
        .replace(
            "Subject:",
            ""
        )
        .strip()
    )

    body = "\n".join(
        lines[1:]
    ).strip()


# ==========================
# PRINT
# ==========================

print(
    "\n===================================="
)

print(
    f"📧 Sending email to: "
    f"{business_name}"
)

print(
    f"Receiver : {receiver}"
)

print(
    f"Email    : {email_file}"
)

print(
    "===================================="
)


# ==========================
# CREATE MESSAGE
# ==========================

msg = EmailMessage()

msg["From"] = EMAIL

msg["To"] = receiver

msg["Subject"] = subject

msg.set_content(
    body
)


# ==========================
# SEND
# ==========================

try:

    with smtplib.SMTP(
        "smtp.gmail.com",
        587
    ) as smtp:

        smtp.starttls()

        smtp.login(
            EMAIL,
            PASSWORD
        )

        smtp.send_message(
            msg
        )


    # ==========================
    # MARK SENT
    # ==========================

    leads[target_index]["Status"] = "SENT"


    # ==========================
    # SAVE CSV
    # ==========================

    temp_file = (
        LEADS_FILE + ".tmp"
    )

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

        writer.writerows(
            leads
        )


    os.replace(
        temp_file,
        LEADS_FILE
    )


    print(
        "\n✅ Email Sent Successfully!"
    )

    print(
        f"📌 Status: "
        f"{business_name} → SENT"
    )


except Exception as e:

    print(
        "\n❌ Email Failed"
    )

    print(e)

    raise SystemExit(1)