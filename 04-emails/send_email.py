import os
import csv
import smtplib
from email.message import EmailMessage
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
EMAIL_FILE = "04-emails/generated/email.txt"

# ==========================
# READ GENERATED EMAIL
# ==========================

with open(
    EMAIL_FILE,
    "r",
    encoding="utf-8"
) as f:

    content = f.read()

lines = content.splitlines()

subject = "Website Redesign"
body = content

if (
    lines
    and lines[0].lower().startswith("subject:")
):

    subject = lines[0].replace(
        "Subject:",
        ""
    ).strip()

    body = "\n".join(
        lines[1:]
    ).strip()


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


fieldnames = [
    "Business Name",
    "Business Type",
    "Location",
    "Email",
    "Website",
    "Status"
]


# ==========================
# FIND FIRST UNSENT EMAIL
# ==========================

target_index = None
receiver = None

for index, lead in enumerate(leads):

    email = lead.get(
        "Email",
        ""
    ).strip()

    status = lead.get(
        "Status",
        ""
    ).strip().upper()

    if (
        email
        and status != "SENT"
    ):

        receiver = email
        target_index = index

        break


if receiver is None:

    print(
        "\n⚠️ No unsent leads with email found."
    )

    raise SystemExit(0)


business_name = leads[target_index][
    "Business Name"
]


print(
    f"\n📧 Sending email to: "
    f"{business_name}"
)

print(
    f"Receiver: {receiver}"
)


# ==========================
# CREATE EMAIL
# ==========================

msg = EmailMessage()

msg["From"] = EMAIL
msg["To"] = receiver
msg["Subject"] = subject

msg.set_content(body)


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

        smtp.send_message(msg)


    # ==========================
    # MARK SENT
    # ==========================

    leads[target_index]["Status"] = "SENT"


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


    print(
        "\n✅ Email Sent Successfully!"
    )

    print(
        f"📌 Status updated: "
        f"{business_name} → SENT"
    )


except Exception as e:

    print(
        "\n❌ Email Failed"
    )

    print(e)