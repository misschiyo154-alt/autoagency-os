import csv
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin, urlparse, parse_qs, unquote

INPUT_FILE = "05-leads/leads.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (AutoAgencyOS Lead Research)"
}


def clean_url(url):
    """Convert DuckDuckGo redirect URLs into real URLs."""

    if not url:
        return ""

    url = url.strip()

    if url.startswith("//duckduckgo.com/l/"):

        parsed = urlparse("https:" + url)

        params = parse_qs(parsed.query)

        if "uddg" in params:
            url = unquote(params["uddg"][0])

    if url.startswith("http://") or url.startswith("https://"):
        return url

    return ""


def is_valid_email(email):
    """Reject obvious fake/generic emails."""

    if not email:
        return False

    email = email.lower().strip()

    blocked_emails = [
        "john@email.com",
        "test@example.com",
        "example@example.com",
        "hello@example.com",
        "info@example.com",
        "your@email.com",
        "name@email.com"
    ]

    if email in blocked_emails:
        return False

    blocked_domains = [
        "example.com",
        "sentry.io",
        "wixpress.com"
    ]

    if any(
        email.endswith("@" + domain)
        for domain in blocked_domains
    ):
        return False

    return True


def find_contact_info(url):
    """Try to find an email from a business website."""

    url = clean_url(url)

    if not url:
        return "", ""

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=10
        )

        if response.status_code != 200:
            return "", url

        html = response.text

        emails = re.findall(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            html
        )

        for found_email in emails:

            found_email = found_email.lower().strip()

            if is_valid_email(found_email):
                return found_email, url

        # Try common contact pages
        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        contact_paths = [
            "/contact",
            "/contact-us",
            "/contactus"
        ]

        for path in contact_paths:

            contact_url = urljoin(
                url,
                path
            )

            try:

                contact_response = requests.get(
                    contact_url,
                    headers=HEADERS,
                    timeout=10
                )

                if contact_response.status_code != 200:
                    continue

                contact_emails = re.findall(
                    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                    contact_response.text
                )

                for found_email in contact_emails:

                    found_email = found_email.lower().strip()

                    if is_valid_email(found_email):
                        return found_email, url

            except requests.RequestException:
                continue

        return "", url

    except requests.RequestException:

        return "", url


def search_business(business_name, location):
    """
    Search DuckDuckGo to discover the business website.
    """

    query = f"{business_name} {location}"

    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote(query)
    )

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        if response.status_code != 200:
            return "", ""

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        blocked_domains = [
            "facebook.com",
            "instagram.com",
            "youtube.com",
            "tripadvisor.com",
            "zomato.com",
            "swiggy.com",
            "justdial.com",
            "restaurant-guru.in",
            "latlong.net"
        ]

        for result in soup.select(".result"):

            link = result.select_one(
                ".result__a"
            )

            if not link:
                continue

            href = link.get(
                "href",
                ""
            )

            href = clean_url(href)

            if not href:
                continue

            if any(
                domain in href.lower()
                for domain in blocked_domains
            ):
                continue

            return href, ""

        return "", ""

    except requests.RequestException:

        return "", ""


# ==========================
# LOAD LEADS
# ==========================

with open(
    INPUT_FILE,
    "r",
    newline="",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    leads = list(reader)


# ==========================
# ENRICH
# ==========================

for index, lead in enumerate(
    leads,
    start=1
):

    name = lead["Business Name"]
    location = lead["Location"]

    print(
        f"\n[{index}/{len(leads)}] "
        f"Searching: {name}"
    )

    website = lead.get(
        "Website",
        ""
    ).strip()

    email = lead.get(
        "Email",
        ""
    ).strip()

    # Remove old DuckDuckGo URLs
    website = clean_url(website)

    # Remove fake email
    if not is_valid_email(email):
        email = ""

    # Find website if missing
    if not website:

        website, _ = search_business(
            name,
            location
        )

    # Find email if website exists
    if website and not email:

        email, website = find_contact_info(
            website
        )

    lead["Website"] = website
    lead["Email"] = email

    if email:

        print(
            f"  ✅ Email: {email}"
        )

    elif website:

        print(
            f"  🌐 Website: {website}"
        )

    else:

        print(
            "  ⚠️ No website/email found"
        )


# ==========================
# SAVE
# ==========================

fieldnames = [
    "Business Name",
    "Business Type",
    "Location",
    "Email",
    "Website",
    "Status"
]

with open(
    INPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    writer.writerows(
        leads
    )


print(
    "\n=============================="
)

print(
    "✅ LEAD ENRICHMENT COMPLETED"
)

print(
    "=============================="
)

print(
    f"Processed : {len(leads)} leads"
)

print(
    f"Saved     : {INPUT_FILE}"
)