import os, csv, re, smtplib, argparse
from email.message import EmailMessage
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR=Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR/'.env')
EMAIL=os.getenv('EMAIL')
PASSWORD=os.getenv('EMAIL_PASSWORD')
LEADS_FILE=BASE_DIR/'05-leads'/'leads.csv'
EMAIL_DIR=BASE_DIR/'04-emails'/'generated'

def slugify(name):
    return re.sub(r'[^a-z0-9]+','-',(name or '').lower().replace('&','and')).strip('-')

def send_one(index):
    if not EMAIL or not PASSWORD:
        print('[ERROR] EMAIL / EMAIL_PASSWORD missing in .env')
        return False
    with open(LEADS_FILE,'r',newline='',encoding='utf-8') as f: leads=list(csv.DictReader(f))
    if index<1 or index>len(leads): return False
    lead=leads[index-1]
    receiver=(lead.get('Email') or '').strip()
    name=(lead.get('Business Name') or '').strip()
    if not receiver:
        print(f'[SKIP] {name}: no email')
        return False
    path=EMAIL_DIR/f'{slugify(name)}.txt'
    if not path.exists():
        print(f'[SKIP] {name}: email draft missing')
        return False
    content=path.read_text(encoding='utf-8').strip()
    lines=content.splitlines(); subject='Website Redesign'; body=content
    if lines and lines[0].lower().startswith('subject:'):
        subject=lines[0].split(':',1)[1].strip(); body='\n'.join(lines[1:]).strip()
    msg=EmailMessage(); msg['From']=EMAIL; msg['To']=receiver; msg['Subject']=subject; msg.set_content(body)
    try:
        with smtplib.SMTP('smtp.gmail.com',587,timeout=30) as smtp:
            smtp.starttls(); smtp.login(EMAIL,PASSWORD); smtp.send_message(msg)
    except Exception as exc:
        print(f'[ERROR] {name}: {exc}'); return False
    lead['Status']='SENT'
    lead['Sent At']=__import__('datetime').datetime.now().isoformat(timespec='seconds')
    fields=list(leads[0].keys())
    if 'Sent At' not in fields: fields.append('Sent At')
    with open(LEADS_FILE,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(leads)
    print(f'[SENT] {name} -> {receiver}')
    return True

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--index',type=int); ap.add_argument('--all-ready',action='store_true'); args=ap.parse_args()
    with open(LEADS_FILE,'r',newline='',encoding='utf-8') as f: leads=list(csv.DictReader(f))
    if args.index: send_one(args.index); return
    if args.all_ready:
        for i,l in enumerate(leads,1):
            if (l.get('Status') or '').upper()=='EMAIL_READY': send_one(i)
        return
    print('Use --index N or --all-ready')
if __name__=='__main__': main()
