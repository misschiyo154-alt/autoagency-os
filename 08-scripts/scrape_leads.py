import csv
import requests

business_type = input("Business Type: ")
location = input("Location: ")

query = f"""
[out:json][timeout:25];
area["name"="{location}"]->.searchArea;

(
  node["amenity"="{business_type.lower()}"](area.searchArea);
  way["amenity"="{business_type.lower()}"](area.searchArea);
  relation["amenity"="{business_type.lower()}"](area.searchArea);
);

out center tags;
"""

url = "https://overpass-api.de/api/interpreter"

response = requests.post(url, data=query)

print(response.status_code)
print(response.text)

data = response.json()

with open(
    "05-leads/leads.csv",
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.writer(file)

    writer.writerow([
        "Business Name",
        "Business Type",
        "Location"
    ])

    for item in data["elements"]:

        tags = item.get("tags", {})

        name = tags.get("name")

        if not name:
            continue

        writer.writerow([
            name,
            business_type,
            location
        ])

print(f"\n✅ Saved {len(data['elements'])} leads.")