import os
import sys
import csv
import re
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

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
AGENCY_URL = os.getenv("AGENCY_URL", "https://fda9a12a.autoagency-os.pages.dev/").rstrip("/") + "/"

parser = argparse.ArgumentParser(description="AutoAgencyOS full multi-lead pipeline")
parser.add_argument("--quantity", type=int, default=5)
parser.add_argument("--business-type", type=str, default="businesses")
parser.add_argument("--location", type=str, default="")
parser.add_argument("--generate-website", action="store_true")
parser.add_argument("--generate-email", action="store_true")
parser.add_argument("--git-push", action="store_true")
parser.add_argument("--deploy", action="store_true")
parser.add_argument("--approval-required", action="store_true")
parser.add_argument("--no-approval", action="store_true")
parser.add_argument("--approval-timeout", type=int, default=1800)
args = parser.parse_args()

quantity = max(1, min(args.quantity, 50))
business_type = (args.business_type or os.getenv("DEFAULT_BUSINESS_TYPE", "restaurants")).strip()
location = (args.location or os.getenv("DEFAULT_LOCATION", "New York, USA")).strip()
approval_required = args.approval_required and not args.no_approval


def log(message=""):
    print(str(message), flush=True)


def slugify(name):
    slug = (name or "").lower().strip().replace("&", "and")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def read_leads():
    if not LEADS_FILE.exists():
        return []
    try:
        with open(LEADS_FILE, "r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception as exc:
        log(f"[ERROR] Could not read leads.csv: {exc}")
        return []


def write_leads(rows):
    fields = [
        "Business Name", "Business Type", "Location", "Email",
        "Website", "Phone", "OSM URL", "Demo URL", "Status"
    ]
    existing = set()
    for row in rows:
        existing.update(row.keys())
    fields = [x for x in fields if x in existing or x in rows[0]] if rows else fields
    with open(LEADS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_script(script_path, extra_args=None, timeout=1800):
    script_path = Path(script_path)
    if not script_path.exists():
        log(f"[ERROR] Script not found: {script_path}")
        return False, ""
    command = [PYTHON, str(script_path)] + [str(x) for x in (extra_args or [])]
    log("\n" + "=" * 72)
    log("Running: " + " ".join(command))
    log("=" * 72)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    try:
        result = subprocess.run(
            command,
            cwd=str(BASE_DIR),
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
        output = (result.stdout or "") + (result.stderr or "")
        if output:
            log(output[-12000:])
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        log("[ERROR] Process timed out.")
        return False, "timeout"
    except Exception as exc:
        log(f"[ERROR] Process failed: {exc}")
        return False, str(exc)


def write_pending_approval(items):
    payload = {
        "status": "WAITING_APPROVAL",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "agency_url": AGENCY_URL,
        "items": items,
    }
    APPROVAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    APPROVAL_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def wait_for_approval(payload):
    deadline = time.time() + args.approval_timeout
    log("\n🟡 Waiting for Telegram approval...")
    log("Use /approve all or /approve 1 3 5, or /reject.")
    while time.time() < deadline:
        try:
            current = json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
        except Exception:
            time.sleep(2)
            continue
        status = str(current.get("status", "")).upper()
        if status in {"APPROVED", "REJECTED"}:
            return status == "APPROVED"
        if status == "PARTIAL_APPROVED":
            # Selected items can be sent by Aira. Continue so deployment can happen once.
            return True
        time.sleep(2)
    log("[ERROR] Approval timeout reached.")
    return False


log("=" * 72)
log("AUTOAGENCYOS — FULL MULTI-LEAD PIPELINE")
log(f"Quantity      : {quantity}")
log(f"Business type : {business_type}")
log(f"Location      : {location or 'default'}")
log(f"Agency URL    : {AGENCY_URL}")
log("=" * 72)

# 1. SEARCH
log("\n[1/6] FIND FRESH LEADS")
ok, _ = run_script(SCRAPER, ["--quantity", quantity, "--business-type", business_type, "--location", location])
if not ok:
    sys.exit(1)

# 2. ENRICH
log("\n[2/6] ENRICH LEADS")
ok, _ = run_script(ENRICHER)
if not ok:
    sys.exit(1)

leads = read_leads()[:quantity]
if not leads:
    log("[ERROR] No leads found.")
    sys.exit(1)

# 3. GENERATE ALL WEBSITES + EMAILS
log("\n[3/6] GENERATE WEBSITE + EMAIL FOR EVERY LEAD")
items = []
for index, lead in enumerate(leads, 1):
    name = (lead.get("Business Name") or "").strip()
    btype = (lead.get("Business Type") or business_type).strip()
    loc = (lead.get("Location") or location).strip()
    if not name:
        continue
    slug = slugify(name)
    demo_url = f"{AGENCY_URL}{slug}/"
    lead["Demo URL"] = demo_url
    lead["Status"] = "GENERATING"
    log(f"\n[{index}/{len(leads)}] {name}")
    if args.generate_website:
        ok, _ = run_script(WEBSITE_GENERATOR, [name, btype, loc])
        if not ok:
            lead["Status"] = "WEBSITE_FAILED"
            continue
    if args.generate_email:
        ok, _ = run_script(EMAIL_GENERATOR, [name, btype, loc, AGENCY_URL])
        if not ok:
            lead["Status"] = "EMAIL_FAILED"
            continue
    lead["Status"] = "WAITING_APPROVAL" if approval_required else "EMAIL_READY"
    items.append({
        "index": index,
        "business_name": name,
        "business_type": btype,
        "location": loc,
        "email": (lead.get("Email") or "").strip(),
        "slug": slug,
        "demo_url": demo_url,
        "email_file": f"04-emails/generated/{slug}.txt",
        "approval": "PENDING" if approval_required else "APPROVED",
    })

write_leads(leads)
if not items:
    log("[ERROR] No lead completed website/email generation.")
    sys.exit(1)

# 4. APPROVAL
if approval_required:
    payload = write_pending_approval(items)
    if not wait_for_approval(payload):
        for lead in leads:
            if lead.get("Status") == "WAITING_APPROVAL":
                lead["Status"] = "REJECTED"
        write_leads(leads)
        log("No approved leads. Nothing was published/emailed.")
        sys.exit(0)
    try:
        payload = json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
    except Exception:
        payload = payload

# 5. SEND ONLY APPROVED OUTREACH
approved_indexes = []
if approval_required:
    approved_indexes = [int(item.get("index")) for item in payload.get("items", []) if str(item.get("approval", "")).upper() == "APPROVED"]
else:
    approved_indexes = [int(item.get("index")) for item in items]
log(f"\n[5/7] SEND APPROVED EMAILS: {approved_indexes or 'none'}")
for idx in approved_indexes:
    ok, _ = run_script(BASE_DIR / "04-emails" / "send_email.py", ["--index", idx])
    if not ok:
        log(f"[WARNING] Email send failed for lead #{idx}; continuing.")

# 6. DEPLOY WEBSITE DEMOS
log("\n[6/7] PREPARE AGENCY DEMOS")
if args.deploy:
    ok, _ = run_script(REDIRECT_UPDATER)
    if not ok:
        sys.exit(1)
else:
    log("[SKIP] Deploy config disabled.")

# 7. PUSH EVERYTHING GENERATED — website demos are previews; approval controls outreach.
log("\n[7/7] GITHUB PUSH / CLOUDFLARE")
if args.git_push:
    ok, _ = run_script(GIT_PUSHER)
    if not ok:
        sys.exit(1)
else:
    log("[SKIP] Git push disabled.")

# Mark approval file as complete while retaining item choices for Aira/email sender.
try:
    final = json.loads(APPROVAL_FILE.read_text(encoding="utf-8")) if APPROVAL_FILE.exists() else {}
    final["status"] = "READY_TO_SEND"
    final["completed_at"] = datetime.now().isoformat(timespec="seconds")
    APPROVAL_FILE.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")
except Exception:
    pass

log("\n" + "=" * 72)
log("AUTOAGENCYOS PIPELINE READY")
log(f"Generated demos : {len(items)}")
log(f"Agency URL      : {AGENCY_URL}")
log("Approval        : Telegram controlled")
log("Old demos       : preserved")
log("New demos       : added to agency portfolio")
log("=" * 72)
