import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load .env
load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")

# -------------------------
# Receiver Details
# -------------------------

receiver = input("Receiver Email: ")

# -------------------------
# Read Generated Email
# -------------------------

with open("04-emails/generated/email.txt", "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()

subject = "Website Redesign"

body = content

# If first line starts with Subject:
if lines and lines[0].lower().startswith("subject:"):
    subject = lines[0].replace("Subject:", "").strip()
    body = "\n".join(lines[1:]).strip()

# -------------------------
# Create Email
# -------------------------

msg = EmailMessage()

msg["From"] = EMAIL
msg["To"] = receiver
msg["Subject"] = subject

msg.set_content(body)

# -------------------------
# Send
# -------------------------

try:
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(EMAIL, PASSWORD)
        smtp.send_message(msg)

    print("\n✅ Email Sent Successfully!")

except Exception as e:
    print("\n❌ Email Failed")
    print(e)