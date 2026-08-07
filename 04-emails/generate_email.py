import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

business_name = input("Business Name: ")
business_type = input("Business Type: ")
location = input("Location: ")
demo_url = input("Demo Website URL: ")

with open("04-emails/email-prompt.md", "r", encoding="utf-8") as f:
    prompt = f.read()

prompt = prompt.format(
    business_name=business_name,
    business_type=business_type,
    location=location,
    demo_url=demo_url
)

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=prompt,
)

email = response.text

os.makedirs("04-emails/generated", exist_ok=True)

with open("04-emails/generated/email.txt", "w", encoding="utf-8") as f:
    f.write(email)

print("\n✅ Email Generated!")
print(email)