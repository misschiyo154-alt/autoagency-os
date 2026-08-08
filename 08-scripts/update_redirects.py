import csv
import re

LEADS_FILE = "05-leads/leads.csv"
REDIRECTS_FILE = "_redirects"


def create_slug(business_name):

    slug = business_name.lower()

    slug = slug.replace("&", "and")

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        slug
    )

    return slug.strip("-")


routes = []

with open(
    LEADS_FILE,
    newline="",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    for lead in reader:

        business_name = lead["Business Name"]

        slug = create_slug(
            business_name
        )

        route = (
            f"/{slug}/ "
            f"/{slug}/index.html 200"
        )

        routes.append(route)


with open(
    REDIRECTS_FILE,
    "w",
    encoding="utf-8"
) as file:

    for route in routes:
        file.write(route + "\n")


print("\n==============================")
print("✅ REDIRECTS UPDATED")
print("==============================")

for route in routes:
    print(route)