import os
import sys
import csv
import re
import json
import time
import argparse
import subprocess
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable
LEADS_FILE = BASE_DIR / "05-leads" / "leads.csv"
SCRAPER = BASE_DIR / "08-scripts" / "scrape_leads.py"
ENRICHER = BASE_DIR / "08-scripts" / "enrich_leads.py"
WEBSITE_GENERATOR = BASE_DIR / "08-scripts" / "generate_website.py"
GIT_PUSHER = BASE_DIR / "08-scripts" / "git_push.py"
REDIRECT_UPDATER = BASE_DIR / "08-scripts" / "update_redirects.py"
EMAIL_GENERATOR = BASE_DIR / "04-emails" / "generate_email.py"
APPROVAL_FILE = BASE_DIR / "09-history" / "pending_approval.json"
AGENCY_URL = "https://vickywebagency.pages.dev/"

parser = argparse.ArgumentParser(description="AutoAgencyOS Full Pipeline")
parser.add_argument("--quantity", type=int, default=5)
parser.add_argument("--business-type", type=str, default="businesses")
parser.add_argument("--location", type=str, default="")
parser.add_argument("--generate-website", action="store_true")
parser.add_argument("--git-push", action="store_true")
parser.add_argument("--deploy", action="store_true")
parser.add_argument("--generate-email", action="store_true")
parser.add_argument("--approval-required", action="store_true", help="Wait for Telegram /approve before publish")
parser.add_argument("--no-approval", action="store_true", help="Explicitly bypass approval for local testing")
parser.add_argument("--approval-timeout", type=int, default=1800)
args = parser.parse_args()

quantity = max(1, min(args.quantity, 500))
business_type = (args.business_type or "businesses").strip()
location = (args.location or "").strip()

# Production publishing requires approval unless explicitly bypassed.
approval_required = (args.approval_required or (args.git_push or args.deploy)) and not args.no_approval


def log(message=""):
    print(str(message), flush=True)


def run_script(script_path, input_text=None, extra_args=None, timeout=1800):
    script_path = Path(script_path)
    if not script_path.exists():
        log(f"[ERROR] Script not found: {script_path}")
        return False, ""
    command = [PYTHON, str(script_path)]
    if extra_args:
        command.extend(str(x) for x in extra_args)
    log("\n" + "=" * 70)
    log(f"Running: {script_path.name}")
    log("=" * 70)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    try:
        process = subprocess.run(
            command, cwd=str(BASE_DIR), input=input_text, text=True,
            encoding="utf-8", errors="replace", stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, env=env, timeout=timeout
        )
        output = process.stdout or ""
        if output:
            for line in output.splitlines():
                log(line)
        if process.returncode != 0:
            log(f"[ERROR] {script_path.name} exited with code {process.returncode}")
            return False, output
        log(f"[OK] {script_path.name} completed.")
        return True, output
    except subprocess.TimeoutExpired:
        log(f"[ERROR] {script_path.name} timed out.")
        return False, ""
    except KeyboardInterrupt:
        log("[STOPPED] Process cancelled by user.")
        return False, ""
    except Exception as error:
        log(f"[ERROR] Could not execute {script_path.name}: {error}")
        return False, ""


def read_leads():
    if not LEADS_FILE.exists():
        return []
    try:
        with open(LEADS_FILE, "r", newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except Exception as error:
        log(f"[ERROR] Could not read leads.csv: {error}")
        return []


def slugify(name):
    slug = (name or "").lower().strip().replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", slug).strip("-")


def write_pending_approval(lead, demo_url):
    APPROVAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "WAITING_APPROVAL",
        "created_at": time.time(),
        "business_name": lead.get("Business Name", ""),
        "business_type": lead.get("Business Type", business_type),
        "location": lead.get("Location", location),
        "demo_url": demo_url or AGENCY_URL,
        "agency_url": AGENCY_URL,
    }
    APPROVAL_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def wait_for_approval(payload):
    log("\n" + "=" * 70)
    log("APPROVAL REQUIRED BEFORE PRODUCTION PUBLISH")
    log("=" * 70)
    log(f"Business : {payload['business_name']}")
    log(f"Agency   : {AGENCY_URL}")
    log("Telegram: /approve to publish, /reject to cancel")
    log(f"Timeout : {args.approval_timeout // 60} minutes")
    log("Waiting for approval...")
    deadline = time.time() + max(60, args.approval_timeout)
    while time.time() < deadline:
        try:
            if APPROVAL_FILE.exists():
                current = json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
                status = str(current.get("status", "")).upper()
                if status == "APPROVED":
                    log("[APPROVAL] Approved by Boss.")
                    return True
                if status == "REJECTED":
                    log("[APPROVAL] Rejected by Boss.")
                    return False
        except Exception:
            pass
        time.sleep(2)
    log("[APPROVAL] Timed out. Nothing was published.")
    return False


log("\n" + "=" * 70)
log("AUTOAGENCYOS FULL PIPELINE")
log("=" * 70)
log(f"Quantity      : {quantity}")
log(f"Business Type : {business_type}")
log(f"Location      : {location or 'default'}")
log(f"Agency URL    : {AGENCY_URL}")
log(f"Approval      : {'REQUIRED' if approval_required else 'BYPASSED'}")
log("=" * 70)

# 1. SEARCH
log("\n[1/6] LEAD SEARCH")
scrape_ok, _ = run_script(SCRAPER, input_text=f"{business_type}\n{location}\n")
if not scrape_ok:
    sys.exit(1)
rows = read_leads()
if not rows:
    log("[ERROR] No leads found. Pipeline stopped before enrichment.")
    sys.exit(1)

# Respect requested quantity.
fields = list(rows[0].keys())
rows = rows[:quantity]
with open(LEADS_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader(); writer.writerows(rows)
log(f"[OK] {len(rows)} leads selected.")

# 2. ENRICH
log("\n[2/6] LEAD ENRICHMENT")
enrich_ok, _ = run_script(ENRICHER)
if not enrich_ok:
    sys.exit(1)
leads = read_leads()
if not leads:
    log("[ERROR] No leads available after enrichment.")
    sys.exit(1)
lead = leads[0]
lead_name = (lead.get("Business Name") or lead.get("Name") or "").strip()
lead_type = (lead.get("Business Type") or business_type).strip()
lead_location = (lead.get("Location") or location).strip()
if not lead_name:
    log("[ERROR] First lead has no business name.")
    sys.exit(1)

# 3. WEBSITE
log("\n[3/6] WEBSITE GENERATION")
if args.generate_website:
    website_ok, website_output = run_script(WEBSITE_GENERATOR, extra_args=[lead_name, lead_type, lead_location])
    if not website_ok:
        sys.exit(1)
else:
    log("[SKIP] Website generation disabled.")

# 4. EMAIL DRAFT (always uses permanent agency URL)
log("\n[4/6] EMAIL GENERATION")
if args.generate_email:
    email_ok, _ = run_script(EMAIL_GENERATOR, extra_args=[lead_name, lead_type, lead_location, AGENCY_URL])
    if not email_ok:
        log("[WARNING] Email generation failed; continuing.")
else:
    log("[SKIP] Email generation disabled.")

# 5. APPROVAL + DEPLOY CONFIG
if approval_required and (args.git_push or args.deploy):
    payload = write_pending_approval(lead, AGENCY_URL)
    if not wait_for_approval(payload):
        try: APPROVAL_FILE.unlink(missing_ok=True)
        except Exception: pass
        log("Pipeline stopped safely. No GitHub/Cloudflare publish occurred.")
        sys.exit(0)

log("\n[5/6] DEPLOY CONFIG")
if args.deploy:
    deploy_ok, _ = run_script(REDIRECT_UPDATER)
    if not deploy_ok:
        sys.exit(1)
else:
    log("[SKIP] Deploy config disabled.")

# 6. GITHUB PUSH; Cloudflare Pages should auto-deploy from this push.
log("\n[6/6] GITHUB PUSH / CLOUDFLARE TRIGGER")
if args.git_push:
    git_ok, _ = run_script(GIT_PUSHER)
    if not git_ok:
        sys.exit(1)
else:
    log("[SKIP] Git push disabled.")

try: APPROVAL_FILE.unlink(missing_ok=True)
except Exception: pass

log("\n" + "=" * 70)
log("AUTOAGENCYOS PIPELINE FINISHED")
log("=" * 70)
log(f"Lead        : {lead_name}")
log(f"Agency URL  : {AGENCY_URL}")
log(f"Demo route  : {AGENCY_URL}{slugify(lead_name)}/")
log("Old demos   : PRESERVED")
log("Latest demo : UPDATED")
log("Cloudflare  : Git push triggered deployment if Pages is connected to this repo")
log("=" * 70)
