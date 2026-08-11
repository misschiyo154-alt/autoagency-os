import csv
import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import (
    quote,
    urljoin,
    urlparse,
    parse_qs,
    unquote,
)


# ============================================================
# CONFIG
# ============================================================

INPUT_FILE = "05-leads/leads.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36 "
        "AutoAgencyOS/1.0"
    )
}

REQUEST_TIMEOUT = 15


# ============================================================
# SAFE PRINT
# ============================================================

def safe_print(text=""):
    """
    Windows CP1252 console mein emoji ki wajah se crash
    na ho isliye safe printing.
    """

    try:
        print(text)

    except UnicodeEncodeError:
        try:
            print(
                str(text).encode(
                    "ascii",
                    errors="replace"
                ).decode("ascii")
            )

        except Exception:
            pass


# ============================================================
# URL CLEANING
# ============================================================

def clean_url(url):
    """
    DuckDuckGo redirect URL ko real URL mein convert karta hai.
    """

    if not url:
        return ""

    url = str(url).strip()

    if not url:
        return ""

    # DuckDuckGo redirect
    if url.startswith("//duckduckgo.com/l/"):

        try:

            parsed = urlparse(
                "https:" + url
            )

            params = parse_qs(
                parsed.query
            )

            if "uddg" in params:

                url = unquote(
                    params["uddg"][0]
                )

        except Exception:

            return ""

    # Sometimes DDG returns encoded URL
    if "duckduckgo.com/l/" in url:

        try:

            parsed = urlparse(url)

            params = parse_qs(
                parsed.query
            )

            if "uddg" in params:

                url = unquote(
                    params["uddg"][0]
                )

        except Exception:
            pass

    # Only accept HTTP URLs
    if (
        url.startswith("http://")
        or url.startswith("https://")
    ):

        return url.rstrip("/")

    return ""


# ============================================================
# EMAIL VALIDATION
# ============================================================

def is_valid_email(email):
    """
    Obvious fake/invalid emails reject karta hai.
    """

    if not email:
        return False

    email = str(email).lower().strip()

    if not email:
        return False

    # Basic format check
    if not re.match(
        r"^[A-Za-z0-9._%+\-]+@"
        r"[A-Za-z0-9.\-]+\."
        r"[A-Za-z]{2,}$",
        email
    ):
        return False

    blocked_emails = [
        "john@email.com",
        "test@example.com",
        "example@example.com",
        "hello@example.com",
        "info@example.com",
        "your@email.com",
        "name@email.com",
        "email@example.com",
        "user@example.com",
        "admin@example.com",
    ]

    if email in blocked_emails:
        return False

    blocked_domains = [
        "example.com",
        "sentry.io",
        "wixpress.com",
    ]

    domain = email.split("@")[-1]

    if domain in blocked_domains:
        return False

    return True


# ============================================================
# FIND EMAIL ON WEBSITE
# ============================================================

def extract_emails(html):
    """
    HTML se emails extract karta hai.
    """

    if not html:
        return []

    found = re.findall(
        r"[A-Za-z0-9._%+\-]+@"
        r"[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
        html
    )

    results = []

    seen = set()

    for email in found:

        email = (
            email
            .lower()
            .strip()
            .rstrip(".")
            .rstrip(",")
            .rstrip(";")
            .rstrip(":")
        )

        if not email:
            continue

        if email in seen:
            continue

        seen.add(email)

        if is_valid_email(email):

            results.append(email)

    return results


# ============================================================
# FIND CONTACT INFO
# ============================================================

def find_contact_info(url):
    """
    Business website se email discover karta hai.
    """

    url = clean_url(url)

    if not url:

        return "", ""

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        final_url = clean_url(
            response.url
        ) or url

        if response.status_code != 200:

            return "", final_url

        html = response.text

        # ----------------------------------------------------
        # MAIN PAGE
        # ----------------------------------------------------

        emails = extract_emails(
            html
        )

        if emails:

            return (
                emails[0],
                final_url
            )

        # ----------------------------------------------------
        # CONTACT LINKS FROM PAGE
        # ----------------------------------------------------

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        contact_urls = []

        for anchor in soup.find_all(
            "a",
            href=True
        ):

            href = anchor.get(
                "href",
                ""
            ).strip()

            text = anchor.get_text(
                " ",
                strip=True
            ).lower()

            combined = (
                href.lower()
                + " "
                + text
            )

            if any(
                keyword in combined
                for keyword in [
                    "contact",
                    "get in touch",
                    "reach us",
                    "about us"
                ]
            ):

                contact_url = urljoin(
                    final_url,
                    href
                )

                contact_url = clean_url(
                    contact_url
                )

                if contact_url:

                    contact_urls.append(
                        contact_url
                    )

        # Add common contact paths
        for path in [
            "/contact",
            "/contact-us",
            "/contactus",
            "/about",
            "/about-us",
        ]:

            contact_urls.append(
                clean_url(
                    urljoin(
                        final_url,
                        path
                    )
                )
            )

        # Remove duplicates
        unique_urls = []

        seen_urls = set()

        for contact_url in contact_urls:

            if not contact_url:
                continue

            if contact_url in seen_urls:
                continue

            seen_urls.add(
                contact_url
            )

            unique_urls.append(
                contact_url
            )

        # Search contact pages
        for contact_url in unique_urls[:8]:

            try:

                contact_response = requests.get(
                    contact_url,
                    headers=HEADERS,
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=True
                )

                if contact_response.status_code != 200:
                    continue

                contact_emails = extract_emails(
                    contact_response.text
                )

                if contact_emails:

                    return (
                        contact_emails[0],
                        final_url
                    )

            except requests.RequestException:

                continue

        return "", final_url

    except requests.RequestException:

        return "", url

    except Exception:

        return "", url


# ============================================================
# SEARCH BUSINESS WEBSITE
# ============================================================

def search_business(
    business_name,
    location
):
    """
    DuckDuckGo se business website discover karta hai.
    """

    query = (
        f'"{business_name}" '
        f'"{location}"'
    )

    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote(query)
    )

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
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
            "twitter.com",
            "x.com",
            "tripadvisor.com",
            "zomato.com",
            "swiggy.com",
            "justdial.com",
            "restaurant-guru.in",
            "latlong.net",
            "mapquest.com",
            "yelp.com",
            "linkedin.com",
            "practo.com",
        ]

        # ----------------------------------------------------
        # NORMAL DDG RESULTS
        # ----------------------------------------------------

        for result in soup.select(
            ".result"
        ):

            link = result.select_one(
                ".result__a"
            )

            if not link:
                continue

            href = link.get(
                "href",
                ""
            )

            href = clean_url(
                href
            )

            if not href:
                continue

            lower_href = href.lower()

            if any(
                domain in lower_href
                for domain in blocked_domains
            ):
                continue

            return href, ""

        # ----------------------------------------------------
        # FALLBACK: ALL LINKS
        # ----------------------------------------------------

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = link.get(
                "href",
                ""
            )

            href = clean_url(
                href
            )

            if not href:
                continue

            lower_href = href.lower()

            if any(
                domain in lower_href
                for domain in blocked_domains
            ):
                continue

            return href, ""

        return "", ""

    except requests.RequestException:

        return "", ""

    except Exception:

        return "", ""


# ============================================================
# NORMALIZE CSV HEADER
# ============================================================

def normalize_header(header):
    """
    CSV header ko safely normalize karta hai.
    """

    if header is None:
        return ""

    header = str(header)

    # BOM remove
    header = header.replace(
        "\ufeff",
        ""
    )

    # NBSP / weird spaces
    header = header.replace(
        "\xa0",
        " "
    )

    header = header.strip()

    return header


# ============================================================
# NORMALIZE LEAD
# ============================================================

def normalize_lead(lead):
    """
    Existing CSV row ko standard format mein convert karta hai.
    """

    normalized = {}

    for key, value in lead.items():

        clean_key = normalize_header(
            key
        )

        if value is None:
            value = ""

        normalized[clean_key] = str(
            value
        ).strip()

    # --------------------------------------------------------
    # Common alternative header names
    # --------------------------------------------------------

    aliases = {
        "business": "Business Name",
        "business name": "Business Name",
        "name": "Business Name",

        "type": "Business Type",
        "business type": "Business Type",

        "city": "Location",
        "location": "Location",

        "email address": "Email",
        "e-mail": "Email",
        "e-mail address": "Email",
        "email": "Email",

        "url": "Website",
        "site": "Website",
        "website url": "Website",
        "website": "Website",

        "status": "Status",

        "phone number": "Phone",
        "phone": "Phone",

        "address": "Address",

        "demo": "Demo URL",
        "demo url": "Demo URL",
    }

    final = {}

    for key, value in normalized.items():

        lookup = key.lower().strip()

        canonical = aliases.get(
            lookup,
            key
        )

        if (
            canonical not in final
            or not final[canonical]
        ):

            final[canonical] = value

    return final


# ============================================================
# LOAD LEADS SAFELY
# ============================================================

def load_leads():

    try:

        with open(
            INPUT_FILE,
            "r",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            reader = csv.DictReader(
                file
            )

            raw_leads = list(
                reader
            )

    except FileNotFoundError:

        safe_print(
            f"[ERROR] File not found: "
            f"{INPUT_FILE}"
        )

        return []

    except Exception as error:

        safe_print(
            f"[ERROR] CSV read failed: "
            f"{error}"
        )

        return []

    leads = []

    for raw_lead in raw_leads:

        lead = normalize_lead(
            raw_lead
        )

        # ----------------------------------------------------
        # Ensure required fields exist
        # ----------------------------------------------------

        required_fields = [
            "Business Name",
            "Business Type",
            "Location",
            "Email",
            "Website",
            "Status",
        ]

        for field in required_fields:

            if field not in lead:

                lead[field] = ""

        # Preserve optional fields
        if "Phone" not in lead:
            lead["Phone"] = ""

        if "Address" not in lead:
            lead["Address"] = ""

        if "Demo URL" not in lead:
            lead["Demo URL"] = ""

        leads.append(
            lead
        )

    return leads


# ============================================================
# SAVE LEADS
# ============================================================

def save_leads(leads):

    if not leads:

        return False

    fieldnames = [
        "Business Name",
        "Business Type",
        "Location",
        "Email",
        "Website",
        "Phone",
        "Address",
        "Demo URL",
        "Status",
    ]

    temp_file = (
        INPUT_FILE + ".tmp"
    )

    try:

        with open(
            temp_file,
            "w",
            newline="",
            encoding="utf-8"
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

        # Atomic replace
        import os

        os.replace(
            temp_file,
            INPUT_FILE
        )

        return True

    except Exception as error:

        safe_print(
            f"[ERROR] CSV save failed: "
            f"{error}"
        )

        try:

            import os

            if os.path.exists(
                temp_file
            ):

                os.remove(
                    temp_file
                )

        except Exception:
            pass

        return False


# ============================================================
# MAIN
# ============================================================

def main():

    safe_print(
        "=============================="
    )

    safe_print(
        "AutoAgencyOS Lead Enrichment"
    )

    safe_print(
        "=============================="
    )

    leads = load_leads()

    if not leads:

        safe_print(
            "[ERROR] No leads found."
        )

        return 1

    safe_print(
        f"Loaded: {len(leads)} leads"
    )

    # --------------------------------------------------------
    # HEADER CHECK
    # --------------------------------------------------------

    missing_names = 0

    for lead in leads:

        if not (
            lead.get(
                "Business Name",
                ""
            ).strip()
        ):

            missing_names += 1

    if missing_names:

        safe_print(
            f"[WARNING] "
            f"{missing_names} lead(s) "
            f"have no Business Name."
        )

    # --------------------------------------------------------
    # ENRICH
    # --------------------------------------------------------

    for index, lead in enumerate(
        leads,
        start=1
    ):

        name = (
            lead.get(
                "Business Name",
                ""
            )
            or ""
        ).strip()

        location = (
            lead.get(
                "Location",
                ""
            )
            or ""
        ).strip()

        if not name:

            safe_print(
                f"\n[{index}/{len(leads)}] "
                "[SKIP] Missing Business Name"
            )

            continue

        safe_print(
            f"\n[{index}/{len(leads)}] "
            f"Searching: {name}"
        )

        # ----------------------------------------------------
        # EXISTING WEBSITE
        # ----------------------------------------------------

        website = (
            lead.get(
                "Website",
                ""
            )
            or ""
        ).strip()

        email = (
            lead.get(
                "Email",
                ""
            )
            or ""
        ).strip()

        # Clean website
        website = clean_url(
            website
        )

        # Validate email
        if not is_valid_email(
            email
        ):

            email = ""

        # ----------------------------------------------------
        # SEARCH WEBSITE
        # ----------------------------------------------------

        if not website:

            safe_print(
                "  Searching website..."
            )

            website, _ = search_business(
                name,
                location
            )

            website = clean_url(
                website
            )

            if website:

                safe_print(
                    f"  Website: {website}"
                )

        else:

            safe_print(
                f"  Existing website: "
                f"{website}"
            )

        # ----------------------------------------------------
        # FIND EMAIL
        # ----------------------------------------------------

        if website and not email:

            safe_print(
                "  Searching email..."
            )

            email, website = find_contact_info(
                website
            )

        # ----------------------------------------------------
        # SAVE RESULT
        # ----------------------------------------------------

        lead["Website"] = website
        lead["Email"] = email

        if email:

            safe_print(
                f"  Email: {email}"
            )

        elif website:

            safe_print(
                f"  Website only: {website}"
            )

        else:

            safe_print(
                "  No website/email found"
            )

        # ----------------------------------------------------
        # SAVE AFTER EACH LEAD
        # ----------------------------------------------------

        if save_leads(
            leads
        ):

            safe_print(
                "  Saved."
            )

        else:

            safe_print(
                "  WARNING: Save failed."
            )

    # --------------------------------------------------------
    # FINAL SAVE
    # --------------------------------------------------------

    save_leads(
        leads
    )

    safe_print(
        "\n=============================="
    )

    safe_print(
        "LEAD ENRICHMENT COMPLETED"
    )

    safe_print(
        "=============================="
    )

    safe_print(
        f"Processed : {len(leads)} leads"
    )

    safe_print(
        f"Saved     : {INPUT_FILE}"
    )

    # Count
    emails_found = sum(
        1
        for lead in leads
        if is_valid_email(
            lead.get(
                "Email",
                ""
            )
        )
    )

    websites_found = sum(
        1
        for lead in leads
        if clean_url(
            lead.get(
                "Website",
                ""
            )
        )
    )

    safe_print(
        f"Websites  : {websites_found}"
    )

    safe_print(
        f"Emails    : {emails_found}"
    )

    return 0


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )