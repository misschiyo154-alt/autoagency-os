import csv
import os
import sys
import time
import requests


# ============================================================
# WINDOWS UTF-8 FIX
# ============================================================

try:
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace"
    )
    sys.stderr.reconfigure(
        encoding="utf-8",
        errors="replace"
    )
except Exception:
    pass


# ============================================================
# PATHS
# ============================================================

OUTPUT_FILE = os.path.join(
    "05-leads",
    "leads.csv"
)

os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)


# ============================================================
# INPUT
# ============================================================

if len(sys.argv) >= 3:

    business_type = sys.argv[1].strip().lower()
    location = sys.argv[2].strip().lower()

else:

    business_type = input(
        "Business Type: "
    ).strip().lower()

    location = input(
        "Location: "
    ).strip().lower()


# ============================================================
# SPELLING FIXES
# ============================================================

business_type_aliases = {

    "resturant": "restaurant",
    "restraunt": "restaurant",
    "restaurent": "restaurant",

    "doctor": "doctors",
    "dr": "doctors",
    "clinic": "doctors",
    "medical": "doctors",

    "hotel": "hotel",
    "hotels": "hotel",

    "dentist": "dentist",
    "dentists": "dentist",

    "gym": "gym",
    "gyms": "gym",

    "salon": "hairdresser",
    "salons": "hairdresser",
    "beauty salon": "beauty",

    "cafe": "cafe",
    "cafes": "cafe",

    "restaurant": "restaurant",
    "restaurants": "restaurant",
}


business_type = business_type_aliases.get(
    business_type,
    business_type
)


# ============================================================
# CITY COORDINATES
# ============================================================

LOCATIONS = {

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
    },

}


if location not in LOCATIONS:

    print(
        f"ERROR: Location '{location}' is not configured."
    )

    print(
        "Supported locations: "
        "Bhilai, Durg, Raipur"
    )

    sys.exit(1)


lat = LOCATIONS[location]["lat"]
lon = LOCATIONS[location]["lon"]


# ============================================================
# BUSINESS QUERIES
# ============================================================

def build_query(
    business_type,
    lat,
    lon
):

    radius = 15000

    # --------------------------------------------------------
    # DOCTORS
    # --------------------------------------------------------

    if business_type == "doctors":

        return f"""
[out:json][timeout:60];

(
    nwr["amenity"="clinic"](around:{radius},{lat},{lon});
    nwr["amenity"="doctors"](around:{radius},{lat},{lon});
    nwr["healthcare"="doctor"](around:{radius},{lat},{lon});
    nwr["healthcare"="clinic"](around:{radius},{lat},{lon});
    nwr["healthcare"="centre"](around:{radius},{lat},{lon});
    nwr["healthcare"="center"](around:{radius},{lat},{lon});
);

out center tags;
"""


    # --------------------------------------------------------
    # DENTISTS
    # --------------------------------------------------------

    if business_type == "dentist":

        return f"""
[out:json][timeout:60];

(
    nwr["amenity"="dentist"](around:{radius},{lat},{lon});
    nwr["healthcare"="dentist"](around:{radius},{lat},{lon});
);

out center tags;
"""


    # --------------------------------------------------------
    # RESTAURANTS
    # --------------------------------------------------------

    if business_type == "restaurant":

        return f"""
[out:json][timeout:60];

(
    nwr["amenity"="restaurant"](around:{radius},{lat},{lon});
);

out center tags;
"""


    # --------------------------------------------------------
    # CAFE
    # --------------------------------------------------------

    if business_type == "cafe":

        return f"""
[out:json][timeout:60];

(
    nwr["amenity"="cafe"](around:{radius},{lat},{lon});
);

out center tags;
"""


    # --------------------------------------------------------
    # HOTEL
    # --------------------------------------------------------

    if business_type == "hotel":

        return f"""
[out:json][timeout:60];

(
    nwr["tourism"="hotel"](around:{radius},{lat},{lon});
    nwr["tourism"="guest_house"](around:{radius},{lat},{lon});
);

out center tags;
"""


    # --------------------------------------------------------
    # GYM
    # --------------------------------------------------------

    if business_type == "gym":

        return f"""
[out:json][timeout:60];

(
    nwr["leisure"="fitness_centre"](around:{radius},{lat},{lon});
    nwr["sport"="fitness"](around:{radius},{lat},{lon});
);

out center tags;
"""


    # --------------------------------------------------------
    # HAIRDRESSER
    # --------------------------------------------------------

    if business_type == "hairdresser":

        return f"""
[out:json][timeout:60];

(
    nwr["shop"="hairdresser"](around:{radius},{lat},{lon});
);

out center tags;
"""


    # --------------------------------------------------------
    # BEAUTY
    # --------------------------------------------------------

    if business_type == "beauty":

        return f"""
[out:json][timeout:60];

(
    nwr["shop"="beauty"](around:{radius},{lat},{lon});
);

out center tags;
"""


    # --------------------------------------------------------
    # GENERIC FALLBACK
    # --------------------------------------------------------

    return f"""
[out:json][timeout:60];

(
    nwr["amenity"="{business_type}"](around:{radius},{lat},{lon});
    nwr["shop"="{business_type}"](around:{radius},{lat},{lon});
    nwr["healthcare"="{business_type}"](around:{radius},{lat},{lon});
);

out center tags;
"""


# ============================================================
# OVERPASS SERVERS
# ============================================================

OVERPASS_SERVERS = [

    "https://overpass-api.de/api/interpreter",

    "https://overpass.kumi.systems/api/interpreter",

    "https://overpass.private.coffee/api/interpreter",

]


# ============================================================
# REQUEST OVERPASS
# ============================================================

def request_overpass(
    query
):

    headers = {

        "User-Agent":
            "AutoAgencyOS/1.0 "
            "(lead-discovery-bot)",

        "Accept":
            "application/json",

    }


    for server_index, url in enumerate(
        OVERPASS_SERVERS,
        start=1
    ):

        print()
        print(
            f"Overpass Server "
            f"{server_index}/{len(OVERPASS_SERVERS)}"
        )

        print(
            url
        )


        for attempt in range(
            1,
            4
        ):

            try:

                print(
                    f"Request attempt "
                    f"{attempt}/3..."
                )


                response = requests.post(

                    url,

                    data=query.encode(
                        "utf-8"
                    ),

                    headers=headers,

                    timeout=90

                )


                print(
                    f"Overpass Status: "
                    f"{response.status_code}"
                )


                if response.status_code == 200:

                    try:

                        return response.json()

                    except ValueError:

                        print(
                            "ERROR: "
                            "Overpass returned invalid JSON."
                        )

                        print(
                            response.text[:1000]
                        )

                        break


                if response.status_code in [
                    429,
                    502,
                    503,
                    504
                ]:

                    print(
                        "Overpass temporarily "
                        "unavailable."
                    )

                else:

                    print(
                        "Overpass request failed."
                    )

                    print(
                        response.text[:1000]
                    )

                    break


            except requests.Timeout:

                print(
                    "Request timed out."
                )


            except requests.RequestException as error:

                print(
                    f"Network error: {error}"
                )


            if attempt < 3:

                wait_time = 5 * attempt

                print(
                    f"Waiting {wait_time}s..."
                )

                time.sleep(
                    wait_time
                )


        print(
            "Trying next Overpass server..."
        )


    return None


# ============================================================
# CLEAN VALUE
# ============================================================

def clean_value(
    value
):

    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# EXTRACT WEBSITE
# ============================================================

def get_website(
    tags
):

    return clean_value(
        tags.get("website")
        or tags.get("contact:website")
        or tags.get("url")
        or ""
    )


# ============================================================
# EXTRACT EMAIL
# ============================================================

def get_email(
    tags
):

    return clean_value(

        tags.get("email")
        or tags.get("contact:email")
        or ""

    )


# ============================================================
# EXTRACT PHONE
# ============================================================

def get_phone(
    tags
):

    return clean_value(

        tags.get("phone")
        or tags.get("contact:phone")
        or tags.get("mobile")
        or ""

    )


# ============================================================
# EXTRACT ADDRESS
# ============================================================

def get_address(
    tags
):

    parts = [

        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:city"),

    ]

    parts = [

        clean_value(x)
        for x in parts
        if clean_value(x)

    ]

    return ", ".join(parts)


# ============================================================
# SAVE CSV
# ============================================================

def save_leads(
    leads
):

    fieldnames = [

        "Business Name",
        "Business Type",
        "Location",
        "Email",
        "Website",
        "Phone",
        "Address",
        "Status",

    ]


    temp_file = (
        OUTPUT_FILE
        + ".tmp"
    )


    try:

        with open(
            temp_file,
            "w",
            newline="",
            encoding="utf-8-sig"
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
            OUTPUT_FILE
        )

        return True


    except Exception as error:

        print(
            f"ERROR: Failed to save CSV: "
            f"{error}"
        )

        if os.path.exists(
            temp_file
        ):

            try:
                os.remove(
                    temp_file
                )
            except Exception:
                pass

        return False


# ============================================================
# MAIN
# ============================================================

print()
print(
    "=============================="
)

print(
    "AutoAgencyOS Lead Scraper"
)

print(
    "=============================="
)

print(
    f"Business Type: {business_type}"
)

print(
    f"Location     : {location}"
)

print(
    f"Coordinates  : {lat}, {lon}"
)


query = build_query(
    business_type,
    lat,
    lon
)


print()
print(
    "Searching OpenStreetMap..."
)


data = request_overpass(
    query
)


if data is None:

    print()
    print(
        "ERROR: All Overpass servers failed."
    )

    print(
        "No changes were made to leads.csv."
    )

    sys.exit(1)


elements = data.get(
    "elements",
    []
)


# ============================================================
# PARSE RESULTS
# ============================================================

leads = []

seen = set()


for item in elements:

    tags = item.get(
        "tags",
        {}
    )


    name = clean_value(
        tags.get("name")
    )


    if not name:

        continue


    # Avoid duplicates
    dedupe_key = (
        name.lower(),
        clean_value(
            tags.get("addr:street")
        ).lower()
    )


    if dedupe_key in seen:

        continue


    seen.add(
        dedupe_key
    )


    email = get_email(
        tags
    )

    website = get_website(
        tags
    )

    phone = get_phone(
        tags
    )

    address = get_address(
        tags
    )


    leads.append({

        "Business Name":
            name,

        "Business Type":
            business_type,

        "Location":
            location,

        "Email":
            email,

        "Website":
            website,

        "Phone":
            phone,

        "Address":
            address,

        "Status":
            "",

    })


# ============================================================
# SAVE
# ============================================================

if not save_leads(
    leads
):

    sys.exit(1)


# ============================================================
# RESULT
# ============================================================

print()
print(
    "=============================="
)

print(
    "LEADS SCRAPED SUCCESSFULLY"
)

print(
    "=============================="
)

print(
    f"Leads : {len(leads)}"
)

print(
    f"Saved : {OUTPUT_FILE}"
)


# ============================================================
# PREVIEW
# ============================================================

if leads:

    print()
    print(
        "First leads:"
    )

    for lead in leads[:10]:

        print(
            f"- {lead['Business Name']}"
        )

        if lead["Phone"]:

            print(
                f"  Phone: "
                f"{lead['Phone']}"
            )

        if lead["Website"]:

            print(
                f"  Website: "
                f"{lead['Website']}"
            )

        if lead["Email"]:

            print(
                f"  Email: "
                f"{lead['Email']}"
            )

else:

    print()
    print(
        "WARNING: No named businesses "
        "were returned by OpenStreetMap."
    )

    print(
        "The CSV was created but contains "
        "zero leads."
    )