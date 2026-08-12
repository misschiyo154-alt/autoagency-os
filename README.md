# AutoAgencyOS

An AI-powered cold outreach system that automatically creates demo websites and outreach emails for businesses.

## Features

- AI Website Generator
- AI Email Generator
- Auto Git Push
- Cloudflare Deploy
- Auto Email Sender
- History Tracking

## Setup

Create a `.env` file:

```env
GEMINI_API_KEY=

EMAIL=

EMAIL_PASSWORD=
```

## Run

```bash
python run.py
```

FINAL WORKFLOW FIXES
- Preview is published to the agency portfolio BEFORE Telegram approval, so Boss receives a real URL.
- Aira recognizes demo/preview requests and returns actual registry URLs instead of [Link].
- Aira can execute GitHub/Cloudflare update requests via git_push.py.
- Client website prompt forbids website URL placeholders.
