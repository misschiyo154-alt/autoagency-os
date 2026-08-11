import csv
import sys
import os
import time
import re
import argparse
from pathlib import Path
from urllib.parse import quote

import requests


# ============================================================
# AUTOAGENCYOS - WORLDWIDE LEAD SCRAPER
# ============================================================

if os.name == "nt":
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

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

LEADS_DIR = BASE_DIR / "05-leads"
OUTPUT_FILE = LEADS_DIR / "leads.csv"

LEADS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# SETTINGS
# ============================================================

NOMINATIM_URL = (
    "https://nominatim.openstreetmap.org/search"
)

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter"
]

HEADERS = {
    "User-Agent": (
        "AutoAgencyOS/1.0 "
        "(lead-research-tool)"
    )
}

REQUEST_TIMEOUT = 45


# ============================================================
# BUSINESS TYPE NORMALIZATION
# ============================================================

BUSINESS_ALIASES = {

    "resturant": "restaurant",
    "restraunt": "restaurant",
    "restaurent": "restaurant",
    "restaurants": "restaurant",

    "hotel": "hotel",
    "hotels": "hotel",

    "hospital": "hospital",
    "hospitals": "hospital",

    "clinic": "clinic",
    "clinics": "clinic",

    "doctor": "doctor",
    "doctors": "doctor",

    "dentist": "dentist",
    "dentists": "dentist",

    "cafe": "cafe",
    "cafes": "cafe",

    "coffee shop": "cafe",
    "coffee shops": "cafe",

    "bakery": "bakery",
    "bakeries": "bakery",

    "salon": "salon",
    "salons": "salon",

    "barber": "barber",
    "barbers": "barber",

    "gym": "gym",
    "gyms": "gym",
    "fitness": "gym",

    "school": "school",
    "schools": "school",

    "college": "college",
    "colleges": "college",

    "university": "university",
    "universities": "university",

    "pharmacy": "pharmacy",
    "pharmacies": "pharmacy",

    "lawyer": "lawyer",
    "lawyers": "lawyer",

    "real estate": "real_estate",
    "real estate agency": "real_estate",

    "car dealer": "car_dealer",
    "car dealers": "car_dealer",

    "auto dealer": "car_dealer",

    "electronics": "electronics",

    "clothing": "clothing",

    "jewelry": "jewelry",
    "jewellery": "jewelry",

    "furniture": "furniture",

    "supermarket": "supermarket",

    "grocery": "supermarket",
    "grocery store": "supermarket",

    "bakery shop": "bakery",

    "business": "businesses",
    "businesses": "businesses",

}


def normalize_business_type(value):

    value = (
        value
        .strip()
        .lower()
    )

    return BUSINESS_ALIASES.get(
        value,
        value
    )


# ============================================================
# SAFE PRINT
# ============================================================

def log(message=""):

    try:
        print(
            message,
            flush=True
        )

    except Exception:

        try:
            print(
                str(message)
                .encode(
                    "ascii",
                    errors="replace"
                )
                .decode("ascii"),
                flush=True
            )

        except Exception:
            pass


# ============================================================
# INPUT
# ============================================================

def get_arguments():

    parser = argparse.ArgumentParser(
        description=(
            "AutoAgencyOS Worldwide Lead Scraper"
        )
    )

    parser.add_argument(
        "--quantity",
        type=int,
        default=None
    )

    parser.add_argument(
        "--business-type",
        type=str,
        default=None
    )

    parser.add_argument(
        "--location",
        type=str,
        default=None
    )

    return parser.parse_args()


# ============================================================
# INTERACTIVE / TELEGRAM COMPATIBILITY
# ============================================================

def get_input():

    args = get_arguments()

    quantity = args.quantity
    business_type = args.business_type
    location = args.location

    # --------------------------------------------------------
    # If run.py sends stdin:
    #
    # business type
    # location
    #
    # read those values automatically.
    # --------------------------------------------------------

    if (
        business_type is None
        or location is None
    ):

        try:

            if not sys.stdin.isatty():

                lines = []

                for line in sys.stdin:
                    line = line.strip()

                    if line:
                        lines.append(line)

                if business_type is None and len(lines) >= 1:
                    business_type = lines[0]

                if location is None and len(lines) >= 2:
                    location = lines[1]

        except Exception:
            pass

    # --------------------------------------------------------
    # Manual terminal mode
    # --------------------------------------------------------

    if not business_type:

        business_type = input(
            "Business Type: "
        ).strip()

    if not location:

        location = input(
            "Location: "
        ).strip()

    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------

    if quantity is None:

        try:

            quantity_text = input(
                "Quantity: "
            ).strip()

            quantity = int(
                quantity_text
            )

        except Exception:

            quantity = 5

    quantity = max(
        1,
        min(quantity, 500)
    )

    business_type = normalize_business_type(
        business_type
    )

    location = location.strip()

    return (
        quantity,
        business_type,
        location
    )


# ============================================================
# GEOCODE WORLDWIDE LOCATION
# ============================================================

def geocode_location(location):

    log("")
    log(
        f"[LOCATION] Searching worldwide location: "
        f"{location}"
    )

    params = {
        "q": location,
        "format": "json",
        "limit": 1,
        "addressdetails": 1
    }

    try:

        response = requests.get(
            NOMINATIM_URL,
            params=params,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:

            log(
                "[ERROR] Location service "
                f"returned HTTP {response.status_code}"
            )

            return None

        data = response.json()

        if not data:

            log(
                f"[ERROR] Location not found: "
                f"{location}"
            )

            return None

        result = data[0]

        lat = float(
            result["lat"]
        )

        lon = float(
            result["lon"]
        )

        display_name = result.get(
            "display_name",
            location
        )

        log(
            f"[LOCATION OK] {display_name}"
        )

        log(
            f"[COORDINATES] "
            f"{lat:.6f}, {lon:.6f}"
        )

        return {
            "lat": lat,
            "lon": lon,
            "display_name": display_name
        }

    except requests.RequestException as e:

        log(
            f"[ERROR] Geocoding failed: {e}"
        )

        return None

    except Exception as e:

        log(
            f"[ERROR] Geocoding parse failed: {e}"
        )

        return None


# ============================================================
# OSM QUERY BUILDER
# ============================================================

def build_query(
    business_type,
    lat,
    lon
):

    # Search radius ~25 km
    radius = 25000

    # --------------------------------------------------------
    # Specific business mappings
    # --------------------------------------------------------

    queries = {

        "restaurant": [
            '["amenity"="restaurant"]'
        ],

        "cafe": [
            '["amenity"="cafe"]'
        ],

        "hospital": [
            '["amenity"="hospital"]'
        ],

        "clinic": [
            '["amenity"="clinic"]'
        ],

        "dentist": [
            '["amenity"="dentist"]'
        ],

        "pharmacy": [
            '["amenity"="pharmacy"]'
        ],

        "school": [
            '["amenity"="school"]'
        ],

        "college": [
            '["amenity"="college"]'
        ],

        "university": [
            '["amenity"="university"]'
        ],

        "hotel": [
            '["tourism"="hotel"]'
        ],

        "bakery": [
            '["shop"="bakery"]'
        ],

        "salon": [
            '["shop"="hairdresser"]'
        ],

        "barber": [
            '["shop"="barber"]'
        ],

        "gym": [
            '["leisure"="fitness_centre"]'
        ],

        "supermarket": [
            '["shop"="supermarket"]'
        ],

        "clothing": [
            '["shop"="clothes"]'
        ],

        "jewelry": [
            '["shop"="jewelry"]'
        ],

        "furniture": [
            '["shop"="furniture"]'
        ],

        "electronics": [
            '["shop"="electronics"]'
        ],

        "lawyer": [
            '["office"="lawyer"]'
        ],

        "real_estate": [
            '["office"="estate_agent"]'
        ],

        "car_dealer": [
            '["shop"="car"]'
        ],

    }

    tags = queries.get(
        business_type
    )

    # --------------------------------------------------------
    # Generic business search
    # --------------------------------------------------------

    if not tags:

        tags = [
            '["name"]'
        ]

    parts = []

    for tag in tags:

        parts.append(
            f"""
            node(around:{radius},{lat},{lon}){tag};
            way(around:{radius},{lat},{lon}){tag};
            relation(around:{radius},{lat},{lon}){tag};
            """
        )

    body = "\n".join(parts)

    query = f"""
    [out:json][timeout:40];

    (
        {body}
    );

    out center tags;
    """

    return query


# ============================================================
# OVERPASS SEARCH
# ============================================================

def search_overpass(
    business_type,
    lat,
    lon,
    quantity
):

    query = build_query(
        business_type,
        lat,
        lon
    )

    for endpoint in OVERPASS_ENDPOINTS:

        log("")
        log(
            f"[SEARCH] Using Overpass: "
            f"{endpoint}"
        )

        try:

            response = requests.post(
                endpoint,
                data=query,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code != 200:

                log(
                    f"[WARNING] HTTP "
                    f"{response.status_code}"
                )

                continue

            data = response.json()

            elements = data.get(
                "elements",
                []
            )

            log(
                f"[SEARCH] Raw results: "
                f"{len(elements)}"
            )

            if elements:

                return elements

        except requests.RequestException as e:

            log(
                f"[WARNING] Endpoint failed: "
                f"{e}"
            )

        except Exception as e:

            log(
                f"[WARNING] Parse failed: "
                f"{e}"
            )

        time.sleep(1)

    return []


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(value):

    if not value:
        return ""

    value = str(value)

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# ============================================================
# EXTRACT WEBSITE
# ============================================================

def extract_website(tags):

    possible = [
        "website",
        "contact:website",
        "url"
    ]

    for key in possible:

        value = tags.get(
            key,
            ""
        )

        if value:

            value = value.strip()

            if (
                value.startswith(
                    "http://"
                )
                or
                value.startswith(
                    "https://"
                )
            ):

                return value

            return (
                "https://"
                + value
            )

    return ""


# ============================================================
# EXTRACT PHONE
# ============================================================

def extract_phone(tags):

    for key in [
        "phone",
        "contact:phone",
        "mobile",
        "contact:mobile"
    ]:

        phone = tags.get(
            key,
            ""
        )

        if phone:
            return clean_text(phone)

    return ""


# ============================================================
# BUILD LEAD
# ============================================================

def element_to_lead(
    element,
    business_type,
    location
):

    tags = element.get(
        "tags",
        {}
    )

    name = clean_text(
        tags.get(
            "name",
            ""
        )
    )

    if not name:
        return None

    website = extract_website(
        tags
    )

    phone = extract_phone(
        tags
    )

    # --------------------------------------------------------
    # Coordinates
    # --------------------------------------------------------

    lat = element.get(
        "lat"
    )

    lon = element.get(
        "lon"
    )

    center = element.get(
        "center"
    )

    if lat is None and center:

        lat = center.get(
            "lat"
        )

        lon = center.get(
            "lon"
        )

    # --------------------------------------------------------
    # OSM ID
    # --------------------------------------------------------

    osm_type = element.get(
        "type",
        ""
    )

    osm_id = element.get(
        "id",
        ""
    )

    osm_url = ""

    if osm_type and osm_id:

        osm_url = (
            f"https://www.openstreetmap.org/"
            f"{osm_type}/{osm_id}"
        )

    return {

        "Business Name": name,

        "Business Type": business_type,

        "Location": location,

        "Email": "",

        "Website": website,

        "Phone": phone,

        "OSM URL": osm_url,

        "Status": "NEW"

    }


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def deduplicate(leads):

    seen = set()

    unique = []

    for lead in leads:

        key = (
            lead.get(
                "Business Name",
                ""
            )
            .lower()
            .strip()
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)

        unique.append(
            lead
        )

    return unique


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

        "OSM URL",

        "Status"

    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for lead in leads:

            writer.writerow(
                {
                    field: lead.get(
                        field,
                        ""
                    )
                    for field in fieldnames
                }
            )


# ============================================================
# MAIN
# ============================================================

def main():

    quantity, business_type, location = get_input()

    log("")
    log("=" * 60)
    log("AUTOAGENCYOS WORLDWIDE LEAD SEARCH")
    log("=" * 60)

    log(
        f"Business type : {business_type}"
    )

    log(
        f"Location      : {location}"
    )

    log(
        f"Quantity      : {quantity}"
    )

    log("=" * 60)

    # --------------------------------------------------------
    # GEOCODE
    # --------------------------------------------------------

    geo = geocode_location(
        location
    )

    if not geo:

        log("")
        log(
            "[FAILED] Could not find location."
        )

        sys.exit(1)

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    elements = search_overpass(
        business_type,
        geo["lat"],
        geo["lon"],
        quantity
    )

    if not elements:

        log("")
        log(
            "[FAILED] No businesses found."
        )

        # Create empty CSV anyway
        save_leads([])

        sys.exit(0)

    # --------------------------------------------------------
    # CONVERT
    # --------------------------------------------------------

    leads = []

    for element in elements:

        lead = element_to_lead(
            element,
            business_type,
            location
        )

        if lead:

            leads.append(
                lead
            )

    # --------------------------------------------------------
    # DEDUPLICATE
    # --------------------------------------------------------

    leads = deduplicate(
        leads
    )

    # --------------------------------------------------------
    # LIMIT
    # --------------------------------------------------------

    leads = leads[
        :quantity
    ]

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_leads(
        leads
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    log("")
    log("=" * 60)
    log("LEAD SEARCH COMPLETED")
    log("=" * 60)

    log(
        f"Location : {location}"
    )

    log(
        f"Type     : {business_type}"
    )

    log(
        f"Requested: {quantity}"
    )

    log(
        f"Found    : {len(leads)}"
    )

    log(
        f"Saved    : {OUTPUT_FILE}"
    )

    log("=" * 60)

    if leads:

        log("")
        log("LEADS:")

        for index, lead in enumerate(
            leads,
            start=1
        ):

            log(
                f"{index}. "
                f"{lead['Business Name']}"
            )

            if lead.get(
                "Website"
            ):

                log(
                    f"   Website: "
                    f"{lead['Website']}"
                )

            if lead.get(
                "Phone"
            ):

                log(
                    f"   Phone: "
                    f"{lead['Phone']}"
                )

    log("")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()