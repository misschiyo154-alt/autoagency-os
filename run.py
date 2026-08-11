import os
import sys
import csv
import re
import argparse
import subprocess
from pathlib import Path


# ============================================================
# AUTOAGENCYOS - FULL PIPELINE RUNNER
# ============================================================

# ------------------------------------------------------------
# WINDOWS UTF-8
# ------------------------------------------------------------

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

    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"


# ============================================================
# PROJECT ROOT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

PYTHON = sys.executable


# ============================================================
# FILE PATHS
# ============================================================

LEADS_FILE = (
    BASE_DIR
    / "05-leads"
    / "leads.csv"
)

SCRAPER = (
    BASE_DIR
    / "08-scripts"
    / "scrape_leads.py"
)

ENRICHER = (
    BASE_DIR
    / "08-scripts"
    / "enrich_leads.py"
)

WEBSITE_GENERATOR = (
    BASE_DIR
    / "08-scripts"
    / "generate_website.py"
)

GIT_PUSHER = (
    BASE_DIR
    / "08-scripts"
    / "git_push.py"
)

REDIRECT_UPDATER = (
    BASE_DIR
    / "08-scripts"
    / "update_redirects.py"
)

EMAIL_GENERATOR = (
    BASE_DIR
    / "04-emails"
    / "generate_email.py"
)


# ============================================================
# ARGUMENTS
# ============================================================

parser = argparse.ArgumentParser(
    description="AutoAgencyOS Full Automation Pipeline"
)


parser.add_argument(
    "--quantity",
    type=int,
    default=5,
    help="Number of leads to process"
)


parser.add_argument(
    "--business-type",
    type=str,
    default="businesses",
    help="Business type"
)


parser.add_argument(
    "--location",
    type=str,
    default="",
    help="Worldwide location"
)


parser.add_argument(
    "--generate-website",
    action="store_true",
    help="Generate website for the lead"
)


parser.add_argument(
    "--git-push",
    action="store_true",
    help="Push generated website to Git"
)


parser.add_argument(
    "--deploy",
    action="store_true",
    help="Update redirects/deployment configuration"
)


parser.add_argument(
    "--generate-email",
    action="store_true",
    help="Generate personalized cold email"
)


args = parser.parse_args()


# ============================================================
# NORMALIZE
# ============================================================

quantity = max(
    1,
    args.quantity
)

business_type = (
    args.business_type
    or "businesses"
).strip()

location = (
    args.location
    or ""
).strip()


# ============================================================
# SAFE LOG
# ============================================================

def log(message=""):

    try:

        print(
            str(message),
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
# HEADER
# ============================================================

log()
log("=" * 70)
log("AUTOAGENCYOS FULL PIPELINE")
log("=" * 70)

log(
    f"Quantity      : {quantity}"
)

log(
    f"Business Type : {business_type}"
)

log(
    f"Location      : "
    f"{location if location else 'default'}"
)

log(
    f"Project       : {BASE_DIR}"
)

log("=" * 70)


# ============================================================
# RUN SCRIPT
# ============================================================

def run_script(
    script_path,
    input_text=None,
    extra_args=None
):

    script_path = Path(
        script_path
    )

    if not script_path.exists():

        log()
        log(
            f"[ERROR] Script not found:"
        )

        log(
            str(script_path)
        )

        return False, ""


    command = [
        PYTHON,
        str(script_path)
    ]


    if extra_args:

        command.extend(
            [
                str(x)
                for x in extra_args
            ]
        )


    log()
    log("=" * 70)

    log(
        f"Running: {script_path.name}"
    )

    log(
        "Command: "
        + " ".join(
            f'"{x}"'
            if " " in str(x)
            else str(x)
            for x in command
        )
    )

    log("=" * 70)


    env = os.environ.copy()

    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"


    try:

        process = subprocess.run(

            command,

            cwd=str(BASE_DIR),

            input=input_text,

            text=True,

            encoding="utf-8",

            errors="replace",

            stdout=subprocess.PIPE,

            stderr=subprocess.STDOUT,

            env=env
        )


        output = (
            process.stdout
            or ""
        )


        if output:

            for line in output.splitlines():

                log(line)


        if process.returncode != 0:

            log()

            log(
                f"[ERROR] "
                f"{script_path.name} "
                f"exited with code "
                f"{process.returncode}"
            )

            return False, output


        log()

        log(
            f"[OK] "
            f"{script_path.name} completed."
        )

        return True, output


    except KeyboardInterrupt:

        log()
        log(
            "[STOPPED] "
            "Process cancelled by user."
        )

        return False, ""


    except Exception as error:

        log()

        log(
            "[ERROR] Could not execute:"
        )

        log(
            str(script_path)
        )

        log(
            str(error)
        )

        return False, ""


# ============================================================
# LEAD SCRAPER
# ============================================================

log()
log("[1/6] LEAD SEARCH")


if not SCRAPER.exists():

    log(
        "[ERROR] scrape_leads.py not found."
    )

    sys.exit(1)


scraper_input = (
    f"{business_type}\n"
    f"{location}\n"
)


scrape_ok, scrape_output = run_script(
    SCRAPER,
    input_text=scraper_input
)


if not scrape_ok:

    log()
    log(
        "Lead search failed."
    )

    sys.exit(1)


# ============================================================
# LIMIT CSV
# ============================================================

log()
log(
    "[PIPELINE] Limiting leads "
    f"to {quantity}."
)


if not LEADS_FILE.exists():

    log(
        "[ERROR] leads.csv was not created."
    )

    sys.exit(1)


try:

    with open(
        LEADS_FILE,
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(
            file
        )

        fieldnames = (
            reader.fieldnames
        )

        rows = list(reader)


    if not fieldnames:

        log(
            "[ERROR] leads.csv has no headers."
        )

        sys.exit(1)


    rows = rows[:quantity]


    with open(
        LEADS_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(rows)


    log(
        f"[OK] {len(rows)} leads "
        "selected."
    )


except Exception as error:

    log(
        "[ERROR] Could not process leads.csv:"
    )

    log(error)

    sys.exit(1)


# ============================================================
# ENRICH
# ============================================================

log()
log("[2/6] LEAD ENRICHMENT")


if ENRICHER.exists():

    enrich_ok, enrich_output = run_script(
        ENRICHER
    )

    if not enrich_ok:

        log()
        log(
            "[WARNING] Enrichment failed."
        )

else:

    log(
        "[WARNING] enrich_leads.py not found."
    )


# ============================================================
# READ FIRST LEAD
# ============================================================

def read_leads():

    if not LEADS_FILE.exists():
        return []


    try:

        with open(
            LEADS_FILE,
            "r",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            reader = csv.DictReader(
                file
            )

            return list(reader)

    except Exception as error:

        log(
            "[ERROR] Could not read leads.csv:"
        )

        log(error)

        return []


# ============================================================
# WEBSITE GENERATION
# ============================================================

website_output = ""

demo_url = ""


if args.generate_website:

    log()
    log("[3/6] WEBSITE GENERATION")


    leads = read_leads()


    if not leads:

        log(
            "[ERROR] No leads available "
            "for website generation."
        )

        sys.exit(1)


    # --------------------------------------------------------
    # Current pipeline generates the website for the FIRST
    # selected lead.
    # --------------------------------------------------------

    lead = leads[0]


    lead_name = (
        lead.get("Business Name")
        or lead.get("business_name")
        or lead.get("Name")
        or lead.get("name")
        or ""
    ).strip()


    lead_type = (
        lead.get("Business Type")
        or lead.get("business_type")
        or business_type
        or ""
    ).strip()


    lead_location = (
        lead.get("Location")
        or lead.get("location")
        or location
        or ""
    ).strip()


    if not lead_name:

        log(
            "[ERROR] Could not determine "
            "business name from leads.csv."
        )

        sys.exit(1)


    log()
    log(
        f"[WEBSITE] Business : {lead_name}"
    )

    log(
        f"[WEBSITE] Type     : {lead_type}"
    )

    log(
        f"[WEBSITE] Location : {lead_location}"
    )


    website_ok, website_output = run_script(

        WEBSITE_GENERATOR,

        extra_args=[
            lead_name,
            lead_type,
            lead_location
        ]
    )


    if not website_ok:

        log()
        log(
            "[ERROR] Website generation failed."
        )

        sys.exit(1)


    # --------------------------------------------------------
    # Extract Demo URL printed by generator
    # --------------------------------------------------------

    url_patterns = [

        r"Demo URL\s*:\s*(https?://\S+)",

        r"Demo\s+URL\s*:\s*(https?://\S+)",

        r"(https://autoagency-os\.pages\.dev/\S+)"
    ]


    for pattern in url_patterns:

        match = re.search(
            pattern,
            website_output,
            flags=re.IGNORECASE
        )

        if match:

            demo_url = (
                match.group(1)
                .strip()
                .rstrip(".,)")
            )

            break


    if demo_url:

        log()
        log(
            f"[OK] Demo URL captured:"
        )

        log(
            demo_url
        )

    else:

        log()
        log(
            "[WARNING] Demo URL could not "
            "be detected from generator output."
        )


else:

    log()
    log(
        "[3/6] Website generation skipped."
    )


# ============================================================
# GIT PUSH
# ============================================================

if args.git_push:

    log()
    log("[4/6] GIT PUSH")


    if not GIT_PUSHER.exists():

        log(
            "[ERROR] git_push.py not found."
        )

        sys.exit(1)


    git_ok, git_output = run_script(
        GIT_PUSHER
    )


    if not git_ok:

        log()
        log(
            "[ERROR] Git push failed."
        )

        sys.exit(1)


else:

    log()
    log(
        "[4/6] Git push skipped."
    )


# ============================================================
# DEPLOY / REDIRECTS
# ============================================================

if args.deploy:

    log()
    log("[5/6] DEPLOY / REDIRECT UPDATE")


    if REDIRECT_UPDATER.exists():

        redirect_ok, redirect_output = run_script(
            REDIRECT_UPDATER
        )


        if not redirect_ok:

            log()
            log(
                "[WARNING] Redirect/deploy "
                "script failed."
            )

    else:

        log(
            "[WARNING] update_redirects.py "
            "not found."
        )

else:

    log()
    log(
        "[5/6] Deploy step skipped."
    )


# ============================================================
# EMAIL GENERATION
# ============================================================

if args.generate_email:

    log()
    log("[6/6] EMAIL GENERATION")


    leads = read_leads()


    if not leads:

        log(
            "[ERROR] No leads available "
            "for email generation."
        )

        sys.exit(1)


    # --------------------------------------------------------
    # Generate email for first selected lead.
    # --------------------------------------------------------

    lead = leads[0]


    lead_name = (
        lead.get("Business Name")
        or lead.get("business_name")
        or lead.get("Name")
        or lead.get("name")
        or ""
    ).strip()


    lead_type = (
        lead.get("Business Type")
        or lead.get("business_type")
        or business_type
        or ""
    ).strip()


    lead_location = (
        lead.get("Location")
        or lead.get("location")
        or location
        or ""
    ).strip()


    # --------------------------------------------------------
    # If website generator didn't return a URL, use the
    # default demo URL based on the business slug.
    # --------------------------------------------------------

    if not demo_url and lead_name:

        slug = lead_name.lower()

        slug = slug.replace(
            "&",
            "and"
        )

        slug = re.sub(
            r"[^a-z0-9]+",
            "-",
            slug
        )

        slug = slug.strip("-")


        if slug:

            demo_url = (
                "https://autoagency-os.pages.dev/"
                + slug
                + "/"
            )


    if not demo_url:

        log()
        log(
            "[WARNING] No demo URL available."
        )

        log(
            "[WARNING] Email will not be generated "
            "because the prompt requires a real demo URL."
        )

    else:

        log()
        log(
            f"[EMAIL] Demo URL: {demo_url}"
        )


        email_ok, email_output = run_script(

            EMAIL_GENERATOR,

            extra_args=[
                lead_name,
                lead_type,
                lead_location,
                demo_url
            ]
        )


        if not email_ok:

            log()
            log(
                "[WARNING] Email generation failed."
            )

else:

    log()
    log(
        "[6/6] Email generation skipped."
    )


# ============================================================
# FINAL STATUS
# ============================================================

log()
log("=" * 70)
log("AUTOAGENCYOS PIPELINE FINISHED")
log("=" * 70)


leads = read_leads()


total_leads = len(
    leads
)


emails_ready = 0


for lead in leads:

    email = (
        lead.get("Email")
        or lead.get("email")
        or ""
    ).strip()


    if email:

        emails_ready += 1


log(
    f"Leads available : {total_leads}"
)

log(
    f"Emails found    : {emails_ready}"
)


if demo_url:

    log(
        f"Demo URL        : {demo_url}"
    )


log("=" * 70)

log()
log(
    "Pipeline complete."
)

sys.exit(0)