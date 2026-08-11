from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
WEBSITE_DIR = BASE_DIR / "02-websites"
ROOT_REDIRECTS = BASE_DIR / "_redirects"
PAGES_REDIRECTS = WEBSITE_DIR / "_redirects"

# Do NOT wildcard-redirect every path. Client demo folders must remain reachable.
# Cloudflare Pages serves /slug/ from /slug/index.html automatically.
content = "/ /index.html 200\n"

for target in (ROOT_REDIRECTS, PAGES_REDIRECTS):
    target.write_text(content, encoding="utf-8")

print("\n==============================")
print("REDIRECTS UPDATED")
print("==============================")
print("Permanent agency URL:")
print("https://vickywebagency.pages.dev/")
print("\nOnly root is explicitly rewritten; client demo routes are preserved.")
