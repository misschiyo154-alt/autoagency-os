import os
import sys
import re
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from google import genai

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
PROMPT_FILE = BASE_DIR / "03-prompts" / "website-generator.md"
WEBSITES_DIR = BASE_DIR / "02-websites"
GENERATED_DIR = WEBSITES_DIR / "generated"
DEMO_INDEX_FILE = WEBSITES_DIR / "demos.json"
AGENCY_INDEX_FILE = WEBSITES_DIR / "index.html"
MAIN_DEMO_URL = os.getenv("AGENCY_URL", "https://fda9a12a.autoagency-os.pages.dev/").rstrip("/") + "/"

load_dotenv(ENV_FILE)
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("[ERROR] GEMINI_API_KEY missing in .env")
    print(f"Expected: {ENV_FILE}")
    sys.exit(1)

try:
    client = genai.Client(api_key=api_key)
except Exception as error:
    print("[ERROR] Could not create Gemini client.")
    print(error)
    sys.exit(1)

if len(sys.argv) == 4:
    business_name = sys.argv[1].strip()
    business_type = sys.argv[2].strip()
    location = sys.argv[3].strip()
else:
    business_name = input("Business Name: ").strip()
    business_type = input("Business Type: ").strip()
    location = input("Location: ").strip()

if not business_name or not business_type or not location:
    print("[ERROR] Business Name, Business Type and Location are required.")
    sys.exit(1)

print("\n" + "=" * 60)
print("AutoAgencyOS Website Generator")
print("=" * 60)
print(f"Business : {business_name}")
print(f"Type     : {business_type}")
print(f"Location : {location}")
print("=" * 60)

if not PROMPT_FILE.exists():
    print(f"[ERROR] Website prompt not found: {PROMPT_FILE}")
    sys.exit(1)

try:
    prompt_template = PROMPT_FILE.read_text(encoding="utf-8")
    prompt = prompt_template.format(
        business_name=business_name,
        business_type=business_type,
        location=location,
    )
except Exception as error:
    print("[ERROR] Could not prepare prompt.")
    print(error)
    sys.exit(1)

print("\n[AI] Generating website with Gemini...")
print("[AI] Please wait...")

try:
    response = client.models.generate_content(
        model=os.getenv("GEMINI_WEBSITE_MODEL", "gemini-3-flash-preview"),
        contents=prompt,
    )
    html = (response.text or "").strip()
except Exception as error:
    print("[ERROR] Gemini API request failed.")
    print(error)
    sys.exit(1)

if not html:
    print("[ERROR] Gemini returned empty website.")
    sys.exit(1)

html = re.sub(r"^\s*```html\s*", "", html, flags=re.IGNORECASE)
html = re.sub(r"^\s*```\s*", "", html)
html = re.sub(r"\s*```\s*$", "", html)

lower = html.lower()
positions = [p for p in [lower.find("<!doctype"), lower.find("<html")] if p >= 0]
if positions:
    html = html[min(positions):]
end = html.lower().rfind("</html>")
if end >= 0:
    html = html[:end + len("</html>")]
html = html.strip()

if len(html) < 100:
    print(f"[ERROR] Generated HTML is suspiciously short: {len(html)}")
    sys.exit(1)

def create_slug(name):
    slug = name.lower().strip().replace("&", "and")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")

slug = create_slug(business_name)
if not slug:
    print("[ERROR] Could not create website slug.")
    sys.exit(1)

client_folder = WEBSITES_DIR / slug
client_folder.mkdir(parents=True, exist_ok=True)
client_output = client_folder / "index.html"
client_output.write_text(html, encoding="utf-8")

GENERATED_DIR.mkdir(parents=True, exist_ok=True)
latest_output = GENERATED_DIR / "index.html"
latest_output.write_text(html, encoding="utf-8")

# Build/update a persistent demo registry. Existing client folders are never deleted.
registry = []
if DEMO_INDEX_FILE.exists():
    try:
        import json
        registry = json.loads(DEMO_INDEX_FILE.read_text(encoding="utf-8"))
        if not isinstance(registry, list): registry = []
    except Exception:
        registry = []

registry = [x for x in registry if isinstance(x, dict) and x.get("slug") != slug]
registry.insert(0, {
    "business_name": business_name, "business_type": business_type, "location": location,
    "slug": slug, "url": f"/{slug}/", "created_at": datetime.now().isoformat(timespec="seconds")
})
known = {x.get("slug") for x in registry}
for folder in sorted(WEBSITES_DIR.iterdir()):
    if not folder.is_dir() or folder.name in {"generated", "_drafts"} or folder.name in known:
        continue
    if (folder / "index.html").exists():
        registry.append({"business_name": folder.name.replace("-", " ").title(), "business_type": "Website Demo", "location": "", "slug": folder.name, "url": f"/{folder.name}/", "created_at": ""})
DEMO_INDEX_FILE.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")

if AGENCY_INDEX_FILE.exists():
    agency_html = AGENCY_INDEX_FILE.read_text(encoding="utf-8-sig")
    latest = registry[:6]
    older = registry[6:]
    cards=[]
    for item in latest:
        name=str(item.get("business_name") or "Website Demo").replace('"','&quot;')
        typ=str(item.get("business_type") or "Website Demo").replace('"','&quot;')
        slug_i=item["slug"]
        cards.append('<a class="demo reveal" href="/'+slug_i+'/" target="_blank" rel="noopener noreferrer"><div class="preview"><iframe class="preview-frame" src="/'+slug_i+'/" title="'+name+' live homepage preview" loading="lazy" tabindex="-1"></iframe><div class="preview-label">Live homepage</div><div class="preview-open">Open full preview</div></div><div class="dinfo"><div class="dtype">'+typ+'</div><div class="dname">'+name+'</div><div class="dlink">Tap preview to open full website</div></div></a>')
    archive=[]
    for item in older:
        name=str(item.get("business_name") or "Website Demo").replace('"','&quot;')
        typ=str(item.get("business_type") or "Website Demo").replace('"','&quot;')
        slug_i=item["slug"]
        archive.append('<a class="demo reveal archive-demo" href="/'+slug_i+'/" target="_blank" rel="noopener noreferrer"><div class="preview"><iframe class="preview-frame" src="/'+slug_i+'/" title="'+name+' archived homepage preview" loading="lazy" tabindex="-1"></iframe><div class="preview-label">Archived work</div><div class="preview-open">Open</div></div><div class="dinfo"><div class="dtype">'+typ+'</div><div class="dname">'+name+'</div></div></a>')
    extra=''
    if archive:
        extra='<div class="archive-wrap"><button class="archive-toggle" type="button" onclick="const a=document.getElementById(\'demo-archive\');a.classList.toggle(\'open\');this.textContent=a.classList.contains(\'open\')?\'Hide older work\':\'See more older work\'">See more older work</button></div><div id="demo-archive" class="demos archive">'+''.join(archive)+'</div>'
    section='<section class="sec" id="demos"><div class="container"><div class="head reveal"><div class="kicker">02 — Selected work</div><h2 class="title">Real concepts. Different businesses. One standard.</h2><p class="copy">The six newest concepts are featured here. Older work stays available in the archive.</p></div><div class="demos">'+''.join(cards)+'</div>'+extra+'</div></section>'
    agency_html, replaced = re.subn(r'<section class="sec" id="demos">.*?</section>', section, agency_html, count=1, flags=re.DOTALL)
    if replaced:
        css='.archive-wrap{text-align:center;margin-top:28px}.archive-toggle{border:1px solid rgba(87,199,133,.35);background:rgba(87,199,133,.08);color:var(--green);border-radius:999px;padding:12px 18px;font:600 12px Inter,sans-serif;cursor:pointer}.archive{display:none;margin-top:24px}.archive.open{display:grid}.archive-demo{opacity:.86}'
        if css not in agency_html: agency_html=agency_html.replace('</style>',css+'</style>')
        AGENCY_INDEX_FILE.write_text(agency_html,encoding='utf-8')
    else:
        print('[WARNING] Could not locate agency demos section; homepage left unchanged.')

print("\n" + "=" * 60)
print("WEBSITE GENERATED SUCCESSFULLY")
print("=" * 60)
print(f"Business : {business_name}")
print(f"Slug     : {slug}")
print(f"Client   : {client_output}")
print(f"Latest   : {latest_output}")
print(f"Registry : {DEMO_INDEX_FILE}")
print(f"Agency   : {AGENCY_INDEX_FILE}")
print(f"MAIN URL : {MAIN_DEMO_URL}")
print("=" * 60)
