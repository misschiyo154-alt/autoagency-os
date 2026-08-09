import csv

LEADS_FILE = "05-leads/leads.csv"

FIELDNAMES = [
    "Business Name",
    "Business Type",
    "Location",
    "Email",
    "Website",
    "Demo URL",
    "Status",
]

with open(
    LEADS_FILE,
    "r",
    newline="",
    encoding="utf-8"
) as file:

    reader = csv.reader(file)
    rows = list(reader)

fixed_rows = []

for row in rows[1:]:

    if not row:
        continue

    # Current broken rows contain:
    # Business, Type, Location, Email, [Website, Demo URL, Status]

    business_name = row[0].strip()
    business_type = row[1].strip()
    location = row[2].strip()
    email = row[3].strip()

    remaining = row[4:]

    website = ""
    demo_url = ""
    status = ""

    if len(remaining) >= 1:
        website = remaining[0].strip()

    if len(remaining) >= 2:
        demo_url = remaining[1].strip()

    if len(remaining) >= 3:
        status = remaining[2].strip()

    fixed_rows.append({
        "Business Name": business_name,
        "Business Type": business_type,
        "Location": location,
        "Email": email,
        "Website": website,
        "Demo URL": demo_url,
        "Status": status,
    })

with open(
    LEADS_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=FIELDNAMES
    )

    writer.writeheader()
    writer.writerows(fixed_rows)

print("✅ leads.csv repaired successfully")
print(f"✅ Leads repaired: {len(fixed_rows)}")