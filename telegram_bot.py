import os
import csv
import re
import json
import asyncio
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from threading import Thread, Lock

from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from google import genai


# ============================================================
# LOAD ENV
# ============================================================

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

OWNER_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID"
)

GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY")
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.1-flash-lite"
)


if not TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN missing in .env"
    )

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY or GOOGLE_API_KEY missing in .env"
    )


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

LEADS_FILE = (
    BASE_DIR
    / "05-leads"
    / "leads.csv"
)

RUN_FILE = (
    BASE_DIR
    / "run.py"
)

SCRAPER_FILE = (
    BASE_DIR
    / "08-scripts"
    / "scrape_leads.py"
)

ENRICH_FILE = (
    BASE_DIR
    / "08-scripts"
    / "enrich_leads.py"
)

GENERATE_WEBSITE_FILE = (
    BASE_DIR
    / "08-scripts"
    / "generate_website.py"
)

GENERATE_EMAIL_FILE = (
    BASE_DIR
    / "04-emails"
    / "generate_email.py"
)

SEND_EMAIL_FILE = (
    BASE_DIR
    / "04-emails"
    / "send_email.py"
)

APPROVAL_FILE = BASE_DIR / "09-history" / "pending_approval.json"
AGENCY_URL = os.getenv("AGENCY_URL", "https://fda9a12a.autoagency-os.pages.dev/").rstrip("/") + "/"
approval_notified_key = None


# ============================================================
# AIRA SETTINGS
# ============================================================

AIRA_NAME = "Aira"

workflow_lock = Lock()

workflow_running = False

workflow_process = None

conversation_history = []

MAX_DAILY_LEADS = 50


# ============================================================
# CURRENT LEAD REQUEST
# ============================================================

current_lead_request = None


# ============================================================
# GEMINI
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)


AIRA_SYSTEM = """
You are Aira, the friendly female executive assistant
of Vicky Web Agency.

The owner is your Boss.

Personality:
- warm
- natural
- intelligent
- slightly playful
- feminine without being childish
- confident
- concise
- understand Hinglish, Hindi and English
- reply in the same language/style Boss uses
- do not sound like customer support
- do not repeatedly say "I understand Boss"
- do not invent business data

Examples:

Boss:
"kya haal hai aira?"

Response:
"Main mast hoon Boss 😄 Aap batao?"

Boss:
"aira kaam chalu karo"

Response:
"Done Boss 😌 Kaam chalu kar diya."

Boss:
"bas 5 doctors ke leads lao"

Meaning:
find_leads
quantity = 5
business_type = doctors

Boss:
"5 dentist ke leads nikaal do"

Meaning:
find_leads
quantity = 5
business_type = dentists

Boss:
"kitne leads aaye?"

Meaning:
leads

IMPORTANT:
"leads" and "find_leads" are DIFFERENT.

"kitne leads aaye?"
=> leads

"5 leads dhundho"
=> find_leads

"doctors ke leads nikaalo"
=> find_leads
"""


# ============================================================
# AI CHAT
# ============================================================

def ask_ai(text, context=""):

    history_text = ""

    if conversation_history:

        history_text = (
            "\nRecent conversation:\n"
        )

        for item in conversation_history[-8:]:

            history_text += (
                f"Boss: {item['user']}\n"
                f"Aira: {item['aira']}\n"
            )

    prompt = f"""
{AIRA_SYSTEM}

Current system context:
{context}

{history_text}

Boss message:
{text}

Reply naturally and briefly.
"""

    try:

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        answer = (
            getattr(
                response,
                "text",
                None
            )
            or
            "Hmm Boss, meri AI side abhi thodi sleepy hai 😅"
        )

        answer = answer.strip()

    except Exception as e:

        print(
            "Gemini chat error:",
            e
        )

        answer = (
            "Boss, AI response mein thoda issue aa gaya 😅"
        )

    conversation_history.append(
        {
            "user": text,
            "aira": answer,
        }
    )

    if len(conversation_history) > 30:

        del conversation_history[:-30]

    return answer


# ============================================================
# OWNER SECURITY
# ============================================================

def is_owner(update: Update):

    if not OWNER_CHAT_ID:
        return True

    try:

        return (
            str(update.effective_chat.id)
            ==
            str(OWNER_CHAT_ID)
        )

    except Exception:

        return False


async def deny(update: Update):

    await update.message.reply_text(
        "Sorry, ye bot sirf Boss ke liye hai. 🙂"
    )


# ============================================================
# LEAD DATA
# ============================================================

def read_leads():

    if not LEADS_FILE.exists():

        return []

    try:

        with open(
            LEADS_FILE,
            "r",
            newline="",
            encoding="utf-8"
        ) as f:

            return list(
                csv.DictReader(f)
            )

    except Exception as e:

        print(
            "CSV read error:",
            e
        )

        return []


# ============================================================
# LEAD STATS
# ============================================================

def lead_stats():

    leads = read_leads()

    total = len(leads)

    sent = 0
    pending = 0
    ready = 0
    failed = 0

    for lead in leads:

        status = (
            lead.get("Status")
            or ""
        ).strip().upper()

        if status == "SENT":

            sent += 1

        elif status == "EMAIL_READY":

            ready += 1

        elif status in [
            "PENDING",
            "WAITING_APPROVAL"
        ]:

            pending += 1

        elif "FAILED" in status:

            failed += 1

    return {
        "total": total,
        "sent": sent,
        "pending": pending,
        "ready": ready,
        "failed": failed,
    }


# ============================================================
# WORKFLOW STATUS
# ============================================================

def workflow_status():

    if workflow_running:

        return "running"

    return "idle"


def status_text():

    stats = lead_stats()

    state = workflow_status()

    if state == "running":

        state_text = "🟢 Running"

    else:

        state_text = "⚪ Idle"

    request_text = ""

    if current_lead_request:

        request_text = (
            "\n\n🔎 Current search:\n"
            f"Quantity: "
            f"{current_lead_request.get('quantity')}\n"
            f"Type: "
            f"{current_lead_request.get('business_type')}\n"
            f"Location: "
            f"{current_lead_request.get('location') or 'Default'}"
        )

    return (
        "🤖 Aira Workflow Status\n\n"
        f"Workflow: {state_text}\n"
        f"Leads: {stats['total']}\n"
        f"Emails sent: {stats['sent']}\n"
        f"Email ready: {stats['ready']}\n"
        f"Pending: {stats['pending']}\n"
        f"Failed: {stats['failed']}"
        f"{request_text}"
    )


# ============================================================
# NORMALIZE BUSINESS TYPE
# ============================================================

def normalize_business_type(value):

    if not value:

        return None

    value = str(value).strip().lower()

    mapping = {

        "doctor": "doctors",
        "doctors": "doctors",

        "dr": "doctors",

        "dentist": "dentists",
        "dentists": "dentists",

        "clinic": "clinics",
        "clinics": "clinics",

        "lawyer": "lawyers",
        "lawyers": "lawyers",

        "restaurant": "restaurants",
        "restaurants": "restaurants",

        "salon": "salons",
        "salons": "salons",

        "gym": "gyms",
        "gyms": "gyms",

        "real estate": "real estate",
        "real estate agents": "real estate",

        "hotel": "hotels",
        "hotels": "hotels",
    }

    return mapping.get(
        value,
        value
    )


# ============================================================
# EXTRACT QUANTITY
# ============================================================

def extract_quantity(text):

    match = re.search(
        r"\b(\d+)\b",
        text.lower()
    )

    if not match:

        return None

    try:

        quantity = int(
            match.group(1)
        )

        if quantity <= 0:

            return None

        if quantity > MAX_DAILY_LEADS:

            quantity = MAX_DAILY_LEADS

        return quantity

    except Exception:

        return None


# ============================================================
# EXTRACT BUSINESS TYPE
# ============================================================

def extract_business_type(text):

    text = text.lower()

    patterns = [

        (
            r"\bdoctors?\b",
            "doctors"
        ),

        (
            r"\bdr\.?\b",
            "doctors"
        ),

        (
            r"\bdentists?\b",
            "dentists"
        ),

        (
            r"\bclinics?\b",
            "clinics"
        ),

        (
            r"\blawyers?\b",
            "lawyers"
        ),

        (
            r"\brestaurants?\b",
            "restaurants"
        ),

        (
            r"\bsalons?\b",
            "salons"
        ),

        (
            r"\bgyms?\b",
            "gyms"
        ),

        (
            r"\bhotels?\b",
            "hotels"
        ),

        (
            r"\breal estate\b",
            "real estate"
        ),
    ]

    for pattern, value in patterns:

        if re.search(
            pattern,
            text
        ):

            return value

    return None


# ============================================================
# EXTRACT LOCATION
# ============================================================

def extract_location(text):

    text = text.strip()

    lower = text.lower()

    # Explicit location phrases
    patterns = [

        r"(?:location|loc)\s*[:\-]?\s*(.+)$",

        r"(?:in|at|near)\s+([A-Za-z][A-Za-z\s,\-]{2,50})$",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            location = match.group(1).strip()

            # Remove common trailing command words
            location = re.sub(
                r"\b(please|pls|jaldi|jldi|se|ke|do|dena|do bhai)\b",
                "",
                location,
                flags=re.IGNORECASE
            ).strip()

            if location:

                return location

    # Common phrase:
    # "doctors ke leads delhi mein"
    match = re.search(
        r"\b(?:in|mein)\s+([A-Za-z][A-Za-z\s,\-]{2,40})",
        text,
        re.IGNORECASE
    )

    if match:

        location = match.group(1).strip()

        location = re.split(
            r"\b(?:please|pls|jaldi|jldi|ke|do|dena)\b",
            location,
            flags=re.IGNORECASE
        )[0].strip()

        if location:

            return location

    return None


# ============================================================
# DETECT OBVIOUS FIND-LEAD REQUEST
# ============================================================

def looks_like_find_leads(text):

    text = text.lower()

    lead_words = [

        "lead dhundh",
        "leads dhundh",

        "lead dhoondh",
        "leads dhoondh",

        "lead nikaal",
        "leads nikaal",

        "lead lao",
        "leads lao",

        "lead chahiye",
        "leads chahiye",

        "lead find",
        "leads find",

        "find lead",
        "find leads",

        "fresh lead",
        "fresh leads",

        "lead search",
        "leads search",

        "leads do",
        "lead do",
    ]

    return any(
        word in text
        for word in lead_words
    )


# ============================================================
# DETERMINISTIC INTENT
# ============================================================

def deterministic_intent(text):

    lower = text.lower().strip()

    # --------------------------------------------------------
    # FIND LEADS
    # --------------------------------------------------------

    if looks_like_find_leads(
        lower
    ):

        quantity = extract_quantity(
            lower
        )

        business_type = extract_business_type(
            lower
        )

        location = extract_location(
            text
        )

        return {
            "action": "find_leads",
            "quantity": quantity or 5,
            "business_type": business_type,
            "location": location,
        }

    # --------------------------------------------------------
    # APPROVAL / REJECTION
    # --------------------------------------------------------
    if lower.startswith("approve") or lower.startswith("/approve"):
        nums=[int(x) for x in re.findall(r"\d+", lower)]
        return {"action":"approve","indexes":nums,"all":("all" in lower or not nums)}

    if lower.startswith("reject") or lower.startswith("/reject"):
        return {"action":"reject"}

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    stop_words = [

        "workflow band",
        "workflow stop",

        "kaam band",
        "kaam rok",

        "ruk ja",
        "ruk jao",

        "stop workflow",
        "stop",
    ]

    if any(
        word in lower
        for word in stop_words
    ):

        return {
            "action": "stop_workflow"
        }

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    start_words = [

        "workflow start",
        "start workflow",

        "kaam chalu",
        "kaam shuru",

        "work chalu",
        "work shuru",

        "kaam resume",
        "resume work",
    ]

    if any(
        word in lower
        for word in start_words
    ):

        return {
            "action": "start_workflow"
        }

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    status_words = [

        "status",

        "kya chal raha",
        "kya chal rha",

        "workflow working",
        "workflow chal",

        "working hai",
        "system status",
    ]

    if any(
        word in lower
        for word in status_words
    ):

        return {
            "action": "status"
        }

    # --------------------------------------------------------
    # LEAD STATS
    # --------------------------------------------------------

    stats_words = [

        "kitne leads",
        "kitna lead",

        "lead count",
        "lead counts",

        "lead statistics",
        "lead stats",

        "leads ka scene",

        "leads kitne",
    ]

    if any(
        word in lower
        for word in stats_words
    ):

        return {
            "action": "leads"
        }

    return None


# ============================================================
# AI INTENT DETECTION
# ============================================================

def detect_intent(user_text):

    # ========================================================
    # FIRST: DETERMINISTIC
    # ========================================================

    obvious = deterministic_intent(
        user_text
    )

    if obvious:

        print(
            "[INTENT]",
            user_text,
            "=>",
            obvious
        )

        return obvious

    # ========================================================
    # SECOND: GEMINI
    # ========================================================

    prompt = f"""
You are an intent router for an AI agency assistant.

User message:
{user_text}

Return ONLY valid JSON.

Allowed actions:

chat
start_workflow
stop_workflow
status
leads
find_leads
pending
approve
reject
help

Rules:

1. "kitne leads aaye?"
=> leads

2. "leads ka scene?"
=> leads

3. "5 leads dhundho"
=> find_leads

4. "5 doctors ke leads lao"
=> find_leads

5. "doctors ke leads nikaalo"
=> find_leads

6. "10 dentists ke fresh leads chahiye"
=> find_leads

7. "workflow chalu karo"
=> start_workflow

8. "workflow band karo"
=> stop_workflow

9. "pending emails dikhao"
=> pending

Extract:

quantity:
requested number, otherwise null

business_type:
doctor/dentist/clinic/etc, otherwise null

location:
requested location, otherwise null

IMPORTANT:

"leads" means SHOW EXISTING LEAD DATA.

"find_leads" means SEARCH FOR NEW LEADS.

Return exactly:

{{
    "action": "...",
    "quantity": null,
    "business_type": null,
    "location": null,
    "indexes": [],
    "all": false
}}
"""

    try:

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        raw = (
            getattr(
                response,
                "text",
                ""
            )
            or ""
        ).strip()

        raw = raw.replace(
            "```json",
            ""
        ).replace(
            "```",
            ""
        ).strip()

        data = json.loads(
            raw
        )

        allowed = [

            "chat",
            "start_workflow",
            "stop_workflow",
            "status",
            "leads",
            "find_leads",
            "pending",
            "approve",
            "reject",
            "help",
        ]

        if data.get(
            "action"
        ) not in allowed:

            data["action"] = "chat"

        # Normalize extracted values

        if data.get(
            "quantity"
        ):

            try:

                data["quantity"] = int(
                    data["quantity"]
                )

            except Exception:

                data["quantity"] = None

        data["business_type"] = (
            normalize_business_type(
                data.get(
                    "business_type"
                )
            )
        )

        if data.get(
            "location"
        ):

            data["location"] = str(
                data["location"]
            ).strip()

        print(
            "[AI INTENT]",
            data
        )

        return data

    except Exception as e:

        print(
            "Intent detection error:",
            e
        )

        return {
            "action": "chat"
        }


# ============================================================
# RUN SCRIPT
# ============================================================

def run_script(
    script_path,
    input_text=None,
    extra_args=None,
    timeout=60 * 60
):

    try:

        if not script_path.exists():

            return (
                False,
                f"File missing: {script_path.name}"
            )

        command = [
            sys.executable,
            str(script_path)
        ]

        if extra_args:

            command.extend(
                extra_args
            )

        print(
            "[RUN]",
            command
        )

        result = subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            cwd=str(BASE_DIR),
            timeout=timeout
        )

        output = (
            result.stdout
            or result.stderr
            or ""
        )

        return (
            result.returncode == 0,
            output[-5000:]
        )

    except subprocess.TimeoutExpired:

        return (
            False,
            "Process timeout ho gaya."
        )

    except Exception as e:

        return (
            False,
            str(e)
        )


# ============================================================
# WORKFLOW THREAD
# ============================================================

def workflow_worker():

    global workflow_running
    global workflow_process
    global current_lead_request

    with workflow_lock:

        if workflow_running:

            return

        workflow_running = True

    try:

        print(
            "\n🚀 Aira workflow started."
        )

        # ----------------------------------------------------
        # MASTER RUN
        # ----------------------------------------------------

        if RUN_FILE.exists():

            request = (
                current_lead_request
                or {}
            )

            command = [
                sys.executable,
                str(RUN_FILE)
            ]

            # ------------------------------------------------
            # PASS LEAD REQUEST TO run.py
            # ------------------------------------------------

            if request:

                quantity = (
                    request.get(
                        "quantity"
                    )
                    or 5
                )

                business_type = (
                    request.get(
                        "business_type"
                    )
                    or ""
                )

                location = (
                    request.get(
                        "location"
                    )
                    or ""
                )

                command.extend(
                    [
                        "--quantity", str(quantity),
                        "--business-type", str(business_type),
                        "--location", str(location),
                        "--generate-website",
                        "--generate-email",
                        "--deploy",
                        "--git-push",
                        "--approval-required",
                    ]
                )

            # Every Telegram workflow is the full production pipeline, but it pauses for Boss approval before publishing.
            if "--generate-website" not in command:
                command.extend([
                    "--generate-website",
                    "--generate-email",
                    "--deploy",
                    "--git-push",
                    "--approval-required",
                ])

            print(
                "[WORKFLOW COMMAND]",
                command
            )

            workflow_process = subprocess.Popen(

                command,

                cwd=str(BASE_DIR),

                stdout=subprocess.PIPE,

                stderr=subprocess.STDOUT,

                text=True,

                encoding="utf-8",

                errors="replace"
            )

            if workflow_process.stdout:

                for line in (
                    workflow_process.stdout
                ):

                    line = (
                        line.rstrip()
                    )

                    if line:

                        print(
                            "[WORKFLOW]",
                            line
                        )

                    if not workflow_running:

                        try:

                            workflow_process.terminate()

                        except Exception:

                            pass

                        break

            try:
                workflow_process.wait()
            except Exception as error:
                print("Workflow wait error:", error)

        else:

            print(
                "run.py not found."
            )

    except Exception as e:

        print(
            "Workflow error:",
            e
        )

    finally:

        workflow_process = None

        workflow_running = False

        current_lead_request = None

        print(
            "🛑 Aira workflow stopped."
        )


# ============================================================
# START NORMAL WORKFLOW
# ============================================================

def start_workflow():

    global workflow_running

    if workflow_running:

        return False

    Thread(
        target=workflow_worker,
        daemon=True
    ).start()

    return True


# ============================================================
# START LEAD SEARCH
# ============================================================

def start_lead_search(
    quantity,
    business_type,
    location
):

    global current_lead_request
    global workflow_running

    if workflow_running:

        return False

    quantity = (
        quantity
        or 5
    )

    quantity = min(
        int(quantity),
        MAX_DAILY_LEADS
    )

    current_lead_request = {

        "quantity": quantity,

        "business_type": (
            normalize_business_type(
                business_type
            )
            or "businesses"
        ),

        "location": (
            location
            or ""
        ).strip(),
    }

    Thread(
        target=workflow_worker,
        daemon=True
    ).start()

    return True


# ============================================================
# STOP WORKFLOW
# ============================================================

def stop_workflow():

    global workflow_running
    global workflow_process

    workflow_running = False

    if workflow_process:

        try:

            workflow_process.terminate()

        except Exception:

            pass

    return True


# ============================================================
# EXECUTE INTENT
# ============================================================

async def execute_intent(
    update: Update,
    intent,
    original_text
):

    action = intent.get(
        "action",
        "chat"
    )
    if action == "approve":
        intent["indexes"] = [int(x) for x in (intent.get("indexes") or []) if str(x).isdigit()]
        intent["all"] = bool(intent.get("all"))

    # ========================================================
    # CHAT
    # ========================================================

    if action == "chat":

        context = status_text()

        answer = ask_ai(
            original_text,
            context
        )

        await update.message.reply_text(
            answer
        )

        return

    # ========================================================
    # FIND LEADS
    # ========================================================

    if action == "find_leads":

        quantity = (
            intent.get(
                "quantity"
            )
            or extract_quantity(
                original_text
            )
            or 5
        )

        business_type = (
            intent.get(
                "business_type"
            )
            or extract_business_type(
                original_text
            )
            or "businesses"
        )

        location = (
            intent.get(
                "location"
            )
            or extract_location(
                original_text
            )
            or ""
        )

        business_type = (
            normalize_business_type(
                business_type
            )
        )

        if workflow_running:

            await update.message.reply_text(
                "Boss, ek workflow already chal raha hai 😅\n\n"
                "Pehle usko finish/stop hone do, phir "
                "main ye search chalaungi."
            )

            return

        start_lead_search(
            quantity=quantity,
            business_type=business_type,
            location=location
        )

        location_text = (
            location
            if location
            else "default location"
        )

        await update.message.reply_text(
            "🔎 Done Boss.\n\n"
            f"Fresh leads search chalu kar di.\n"
            f"👥 Quantity: {quantity}\n"
            f"🏥 Type: {business_type}\n"
            f"📍 Location: {location_text}\n\n"
            "Aira background mein kaam kar rahi hai 😌"
        )

        return

    # ========================================================
    # START
    # ========================================================

    if action == "start_workflow":

        if workflow_running:

            await update.message.reply_text(
                "Boss, workflow already chal raha hai 😄"
            )

            return

        start_workflow()

        await update.message.reply_text(
            "🚀 Done Boss.\n\n"
            "Workflow chalu kar diya hai.\n"
            "Aira background mein kaam dekh rahi hai."
        )

        return

    # ========================================================
    # STOP
    # ========================================================

    if action == "stop_workflow":

        if not workflow_running:

            await update.message.reply_text(
                "Boss, abhi workflow idle hai 😄"
            )

            return

        stop_workflow()

        await update.message.reply_text(
            "🛑 Theek hai Boss.\n"
            "Workflow rok diya."
        )

        return

    # ========================================================
    # STATUS
    # ========================================================

    if action == "status":

        await update.message.reply_text(
            status_text()
        )

        return

    # ========================================================
    # LEADS STATS
    # ========================================================

    if action == "leads":

        stats = lead_stats()

        await update.message.reply_text(
            "📊 Leads ka scene:\n\n"
            f"Total: {stats['total']}\n"
            f"Sent: {stats['sent']}\n"
            f"Email Ready: {stats['ready']}\n"
            f"Pending: {stats['pending']}\n"
            f"Failed: {stats['failed']}"
        )

        return

    # ========================================================
    # PENDING
    # ========================================================

    if action == "pending":

        leads = read_leads()

        pending = []

        for lead in leads:

            status = (
                lead.get("Status")
                or ""
            ).strip().upper()

            if status in [
                "EMAIL_READY",
                "PENDING",
                "WAITING_APPROVAL"
            ]:

                pending.append(
                    lead
                )

        if not pending:

            await update.message.reply_text(
                "Boss, abhi koi pending email nahi hai. 😌"
            )

            return

        message = (
            "📩 Pending emails\n\n"
        )

        for index, lead in enumerate(
            pending[:10],
            1
        ):

            message += (
                f"{index}. "
                f"{lead.get('Business Name', 'Unknown')}\n"
                f"   {lead.get('Email', 'No email')}\n"
                f"   Status: "
                f"{lead.get('Status', '')}\n\n"
            )

        await update.message.reply_text(
            message
        )

        return

    # ========================================================
    # APPROVE
    # ========================================================

    if action == "approve":
        if not APPROVAL_FILE.exists():
            await update.message.reply_text("Boss, abhi koi pending approval nahi hai.")
            return
        try:
            data=json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
            if str(data.get("status", "")).upper() not in {"WAITING_APPROVAL","PARTIAL_APPROVED"}:
                await update.message.reply_text("Boss, abhi active approval request nahi hai.")
                return
            requested=intent.get("indexes") or []
            if intent.get("all") or not requested:
                requested=[int(x.get("index")) for x in data.get("items",[]) if x.get("index") is not None]
            approved=[]
            for item in data.get("items",[]):
                idx=int(item.get("index",0))
                if idx in requested:
                    item["approval"]="APPROVED"; approved.append(idx)
            data["status"]="APPROVED" if approved and len(approved)==len(data.get("items",[])) else "PARTIAL_APPROVED"
            data["approved_indexes"]=approved
            data["approved_at"]=datetime.now().isoformat(timespec="seconds")
            APPROVAL_FILE.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
            await update.message.reply_text("✅ Approved: " + ", ".join(map(str,approved)) + "\nAira approved leads ke emails send karegi aur workflow continue karegi.")
        except Exception as error:
            await update.message.reply_text(f"Boss, approval save nahi hua: {error}")
        return

    # ========================================================
    # REJECT
    # ========================================================

    if action == "reject":

        if not APPROVAL_FILE.exists():
            await update.message.reply_text(
                "Boss, abhi koi pending website approval nahi hai."
            )
            return

        try:
            data = json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
            data["status"] = "REJECTED"
            for item in data.get("items", []): item["approval"] = "REJECTED"
            data["rejected_at"] = datetime.now().isoformat(timespec="seconds")
            APPROVAL_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            await update.message.reply_text(
                "❌ Rejected Boss.\n\n"
                "Is run ka GitHub/Cloudflare publish nahi hoga."
            )
        except Exception as error:
            await update.message.reply_text(f"Boss, reject save nahi hua: {error}")
        return

    # ========================================================
    # HELP
    # ========================================================

    if action == "help":

        await send_help(
            update
        )

        return


# ============================================================
# /START
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await deny(update)

        return

    hour = datetime.now().hour

    if 5 <= hour < 12:

        greeting = "Good morning"

    elif 12 <= hour < 17:

        greeting = "Good afternoon"

    elif 17 <= hour < 21:

        greeting = "Good evening"

    else:

        greeting = "Good night"

    await update.message.reply_text(
        f"{greeting}, Boss 🌸\n\n"
        "Aira online hai.\n"
        "Bolo kya karna hai? 😌"
    )


# ============================================================
# /STATUS
# ============================================================

async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await deny(update)

        return

    await update.message.reply_text(
        status_text()
    )


# ============================================================
# /LEADS
# ============================================================

async def leads_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await deny(update)

        return

    stats = lead_stats()

    await update.message.reply_text(
        "📊 Lead Report\n\n"
        f"Total: {stats['total']}\n"
        f"Sent: {stats['sent']}\n"
        f"Ready: {stats['ready']}\n"
        f"Pending: {stats['pending']}\n"
        f"Failed: {stats['failed']}"
    )


# ============================================================
# /STARTWORKFLOW
# ============================================================

async def start_workflow_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await deny(update)

        return

    if workflow_running:

        await update.message.reply_text(
            "Boss, workflow already running hai 😄"
        )

        return

    start_workflow()

    await update.message.reply_text(
        "🚀 Workflow chalu kar diya Boss.\n"
        "Aira background mein dekh rahi hai."
    )


# ============================================================
# /STOPWORKFLOW
# ============================================================

async def stop_workflow_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await deny(update)

        return

    stop_workflow()

    await update.message.reply_text(
        "🛑 Theek hai Boss, workflow stop kar diya."
    )


# ============================================================
# /PENDING
# ============================================================

async def pending_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await deny(update)

        return

    await execute_intent(
        update,
        {
            "action": "pending"
        },
        "/pending"
    )


# ============================================================
# /APPROVE
# ============================================================

async def approve_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await deny(update)

        return

    await execute_intent(
        update,
        {
            "action": "approve"
        },
        "/approve"
    )


# ============================================================
# /REJECT
# ============================================================

async def reject_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await deny(update)

        return

    await execute_intent(
        update,
        {
            "action": "reject"
        },
        "/reject"
    )


# ============================================================
# HELP
# ============================================================

async def send_help(update):

    await update.message.reply_text(
        "💼 Aira commands\n\n"

        "/start — Aira wake up\n"
        "/status — workflow status\n"
        "/leads — existing lead statistics\n"
        "/startworkflow — workflow start\n"
        "/stopworkflow — workflow stop\n"
        "/pending — pending emails\n"
        "/approve — approve pending\n"
        "/reject — reject pending\n"
        "/help — commands\n\n"

        "Natural language bhi chalegi 😄\n\n"

        "Examples:\n"
        "• 5 doctors ke leads dhundho\n"
        "• 10 dentists ke fresh leads lao\n"
        "• doctors ke leads Delhi mein nikaalo\n"
        "• kitne leads aaye?\n"
        "• leads ka scene kya hai?\n"
        "• workflow chalu karo\n"
        "• workflow band kar do\n"
        "• pending emails dikhao\n"
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await deny(update)

        return

    await send_help(
        update
    )


# ============================================================
# NATURAL MESSAGE HANDLER
# ============================================================

async def message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await deny(update)

        return

    if not update.message:

        return

    text = (
        update.message.text
        or ""
    ).strip()

    if not text:

        return

    print(
        "\n[BOSS]",
        text
    )

    intent = detect_intent(
        text
    )

    print(
        "[FINAL INTENT]",
        intent
    )

    await execute_intent(
        update,
        intent,
        text
    )


# ============================================================
# PERIODIC GREETING
# ============================================================

async def greeting_job(
    context: ContextTypes.DEFAULT_TYPE
):

    if not OWNER_CHAT_ID:

        return

    now = datetime.now()

    hour = now.hour
    minute = now.minute

    greeting = None

    if hour == 7 and minute == 0:

        greeting = (
            "Good morning Boss 🌸\n"
            "Aira online hai. "
            "Aaj ka kaam shuru karna hai toh bas bol dena 😌"
        )

    elif hour == 13 and minute == 0:

        greeting = (
            "Good afternoon Boss ☀️\n"
            "Bas ek chhota sa check-in. "
            "Sab theek chal raha hai."
        )

    elif hour == 18 and minute == 0:

        greeting = (
            "Good evening Boss 🌆\n"
            "Aaj ka progress check karna ho toh "
            "main ready hoon."
        )

    elif hour == 22 and minute == 0:

        greeting = (
            "Good night Boss 🌙\n"
            "Aaj ka kaam kaafi hua. "
            "Aap aaram karo, Aira yahin hai."
        )

    if greeting:

        try:

            await context.bot.send_message(
                chat_id=int(
                    OWNER_CHAT_ID
                ),
                text=greeting
            )

        except Exception as e:

            print(
                "Greeting error:",
                e
            )


# ============================================================
# AUTONOMOUS 24/7 WORKER
# ============================================================

async def autonomous_job(context: ContextTypes.DEFAULT_TYPE):
    if os.getenv("AIRA_AUTONOMOUS", "true").lower() not in {"1", "true", "yes", "on"}:
        return
    if workflow_running or APPROVAL_FILE.exists():
        return
    # Start the same full workflow Aira uses from Telegram, with safe defaults.
    start_lead_search(
        quantity=int(os.getenv("AIRA_AUTO_QUANTITY", "5")),
        business_type=os.getenv("DEFAULT_BUSINESS_TYPE", "restaurants"),
        location=os.getenv("DEFAULT_LOCATION", "New York, USA"),
    )
    if OWNER_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=int(OWNER_CHAT_ID),
                text="🤖 Aira ne autonomous cycle start kar diya — fresh leads → websites → emails → approval."
            )
        except Exception as error:
            print("Autonomous notification error:", error)


# ============================================================
# DAILY LIMIT MONITOR
# ============================================================

async def monitor_job(
    context: ContextTypes.DEFAULT_TYPE
):

    global approval_notified_key

    # Notify Boss when a generated website is waiting for production approval.
    if APPROVAL_FILE.exists() and OWNER_CHAT_ID:
        try:
            data = json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
            if str(data.get("status", "")).upper() == "WAITING_APPROVAL":
                key = f"{data.get('created_at')}:{data.get('business_name')}"
                if key != approval_notified_key:
                    approval_notified_key = key
                    items=data.get("items", [])
                    lines=["🟡 WEBSITE / EMAIL APPROVAL REQUIRED", ""]
                    for item in items:
                        lines.append(f"{item.get('index')}. {item.get('business_name','Unknown')} — {item.get('demo_url',AGENCY_URL)}")
                    lines += ["", f"Agency: {AGENCY_URL}", "", "/approve all  → approve every lead", "/approve 1 3 5 → approve selected leads", "/reject → cancel this batch"]
                    text="\n".join(lines)
                    await context.bot.send_message(chat_id=int(OWNER_CHAT_ID), text=text)
        except Exception as error:
            print("Approval monitor error:", error)

    if not workflow_running:
        return

    stats = lead_stats()

    if stats["total"] >= MAX_DAILY_LEADS:

        stop_workflow()

        if OWNER_CHAT_ID:

            try:

                await context.bot.send_message(

                    chat_id=int(
                        OWNER_CHAT_ID
                    ),

                    text=(
                        "🛑 Daily lead limit reached, Boss.\n\n"
                        f"Current leads: "
                        f"{stats['total']}\n"
                        f"Daily limit: "
                        f"{MAX_DAILY_LEADS}\n\n"
                        "Aira ne workflow pause kar diya."
                    )
                )

            except Exception as e:

                print(
                    "Limit notification error:",
                    e
                )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "🤖 Starting Aira Executive..."
    )

    print(
        f"🧠 Gemini model: "
        f"{GEMINI_MODEL}"
    )

    print(
        "📲 Telegram bot online."
    )

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # --------------------------------------------------------
    # COMMANDS
    # --------------------------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )

    app.add_handler(
        CommandHandler(
            "status",
            status_command
        )
    )

    app.add_handler(
        CommandHandler(
            "leads",
            leads_command
        )
    )

    app.add_handler(
        CommandHandler(
            "startworkflow",
            start_workflow_command
        )
    )

    app.add_handler(
        CommandHandler(
            "stopworkflow",
            stop_workflow_command
        )
    )

    app.add_handler(
        CommandHandler(
            "pending",
            pending_command
        )
    )

    app.add_handler(
        CommandHandler(
            "approve",
            approve_command
        )
    )

    app.add_handler(
        CommandHandler(
            "reject",
            reject_command
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    # --------------------------------------------------------
    # NATURAL LANGUAGE
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            message_handler
        )
    )

    # --------------------------------------------------------
    # SCHEDULER
    # --------------------------------------------------------

    if app.job_queue:

        app.job_queue.run_repeating(
            greeting_job,
            interval=60,
            first=10
        )

        app.job_queue.run_repeating(
            monitor_job,
            interval=5,
            first=5
        )

        app.job_queue.run_repeating(
            autonomous_job,
            interval=3600,
            first=30
        )

    print(
        "\n💗 Aira is ready. Talk naturally."
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()