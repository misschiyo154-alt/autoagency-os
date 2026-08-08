import csv
import requests

# ==========================
# INPUT
# ==========================

business_type = input("Business Type: ").strip().lower()
location = input("Location: ").strip()

# Common spelling fixes
if business_type in ["resturant", "restraunt", "restaurent"]:
    business_type = "restaurant"

# ==========================
# CITY COORDINATES
# ==========================

locations = {
    "bhilai": {
        "lat": 21.2095,
        "lon": 81.4285
    },
    "durg": {
        "lat": 21.1904,
        "lon": 81.2849
    },
    "raipur": {
        "lat": 21.2514,
        "lon": 81.6296
    }
}

location_key = location.lower()

if location_key not in locations:
    print(f"❌ Location '{location}' is not configured yet.")
    print("Currently supported: Bhilai, Durg, Raipur")
    raise SystemExit(1)

lat = locations[location_key]["lat"]
lon = locations[location_key]["lon"]

# ==========================
# OVERPASS QUERY
# ==========================

query = f"""
[out:json][timeout:30];

(
  nwr["amenity"="{business_type}"](around:15000,{lat},{lon});
  nwr["shop"="{business_type}"](around:15000,{lat},{lon});
);

out center tags;
"""

url = "https://overpass-api.de/api/interpreter"

headers = {
    "User-Agent": "AutoAgencyOS/1.0"
}

# ==========================
# REQUEST
# ==========================

try:

    response = requests.post(
        url,
        data=query,
        headers=headers,
        timeout=45
    )

    print(f"Overpass Status: {response.status_code}")

    if response.status_code != 200:

        print("❌ Overpass API Failed")
        print(response.text[:1000])

        raise SystemExit(1)

    data = response.json()

except requests.RequestException as error:

    print(f"❌ Network Error: {error}")
    raise SystemExit(1)

except ValueError:

    print("❌ Invalid JSON returned by Overpass")
    raise SystemExit(1)

# ==========================
# SAVE
# ==========================

output_file = "05-leads/leads.csv"

count = 0

with open(
    output_file,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.writer(file)

    writer.writerow([
        "Business Name",
        "Business Type",
        "Location",
        "Email",
        "Website",
        "Status"
    ])

    for item in data.get("elements", []):

        tags = item.get("tags", {})

        name = tags.get("name")

        if not name:
            continue

        email = (
            tags.get("email")
            or tags.get("contact:email")
            or ""
        )

        website = (
            tags.get("website")
            or tags.get("contact:website")
            or ""
        )

        writer.writerow([
            name,
            business_type,
            location,
            email,
            website,
            ""
        ])

        count += 1

# ==========================
# RESULT
# ==========================

print("\n==============================")
print("✅ LEADS SCRAPED SUCCESSFULLY")
print("==============================")
print(f"Leads : {count}")
print(f"Saved : {output_file}")