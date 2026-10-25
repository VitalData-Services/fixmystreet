#!/usr/bin/env python3
"""Quarterly review of the addresses reports are sent to (owner's rule, 2026-10-26: every 3 months,
automatically and then by hand).

Automatic part, for every municipality's address in data/greece/contacts/dimoi.sql:
  - the domain still has an MX record;
  - for an address from data/greece/dimoi_emails_corrections.csv whose reason names a page (https://…),
    the address is still on that page (rendered in headless Chromium, as many municipal sites need
    JavaScript; plain HTTP if the browser is not there);
  - an address that looks like a person's (name.surname@, n.surname@, …) is listed for review by hand:
    people move, and their mailbox goes with them.
No email is sent and no SMTP check is made.

Usage: review-dimoi-emails.py <repo root> <report.md>
Exit status: 1 when an address cannot receive mail at all, 0 otherwise (the cron wrapper opens a review issue either way).
"""
import csv
import datetime
import re
import subprocess
import sys
import urllib.request

PERSONAL = re.compile(r"^[a-z]{1,3}\.[a-z]{4,}@|^[a-z]{3,}\.[a-z]{4,}@", re.I)   # n.surname@, name.surname@
SERVICE = re.compile(r"(dimos|dimarx|mayor|grafeio|protok|protoc|grammat|gram\.|info|contact|texn|tech|kathar|prasin|sintir|ypodom|perivall|dioik|ypiresia|spetson|dhmos)", re.I)


def a_record(domain):
    return subprocess.run(["dig", "+short", "A", domain], capture_output=True, text=True, timeout=20).stdout.split()


def mx(domain):
    out = subprocess.run(["dig", "+short", "MX", domain], capture_output=True, text=True, timeout=20).stdout
    return [l.split()[-1].rstrip(".") for l in out.splitlines() if l.strip()]


def page_text(url):
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, executable_path="/usr/bin/chromium", args=["--no-sandbox"])
            pg = b.new_context(ignore_https_errors=True, locale="el-GR").new_page()
            pg.goto(url, wait_until="domcontentloaded", timeout=45000)
            pg.wait_for_timeout(4000)
            html = pg.content()
            b.close()
            return html
    except Exception:
        pass
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    except Exception as e:
        return ""


def main(root, report):
    pat = re.compile(r"^  \('((?:[^']|'')*)', '((?:[^']|'')*)', ")
    routing = {}
    for line in open(f"{root}/data/greece/contacts/dimoi.sql", encoding="utf-8"):
        m = pat.match(line)
        if m:
            routing[m.group(1).replace("''", "'")] = m.group(2)
    # Municipalities with their own file (several addresses, one per category): each address once.
    for own, name in (("haidari.sql", "Δήμος Χαϊδαρίου"), ("palaiofaliro.sql", "Δήμος Παλαιού Φαλήρου"), ("piraeus.sql", "Δήμος Πειραιώς"),
                      ("rafina.sql", "Δήμος Ραφήνας - Πικερμίου")):
        try:
            text = open(f"{root}/data/greece/contacts/{own}", encoding="utf-8").read()
        except OSError:
            continue
        for i, email in enumerate(sorted(set(re.findall(r"'([\w.+-]+@[\w.-]+)'", text)))):
            routing[f"{name} ({i + 1})"] = email
    corrections = {r["name_el"]: r for r in csv.DictReader(open(f"{root}/data/greece/dimoi_emails_corrections.csv", encoding="utf-8"))}

    no_mx, a_only, gone, personal, checked = [], [], [], [], 0
    for name, email in sorted(routing.items()):
        local, domain = email.split("@", 1)
        if not mx(domain):
            (a_only if a_record(domain) else no_mx).append((name, email))
        if PERSONAL.search(email) and not SERVICE.search(email):
            personal.append((name, email))
        c = corrections.get(name)
        url = c and re.search(r"https?://\S+", c.get("replaces", "") or "")
        if c and url and c["email_recommended"].lower() == email.lower():
            checked += 1
            if email.lower() not in page_text(url.group(0).rstrip(").,;")).lower():
                gone.append((name, email, url.group(0).rstrip(").,;")))

    today = datetime.date.today().isoformat()
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"# Municipality addresses — quarterly review {today}\n\n")
        f.write(f"{len(routing)} municipalities; {checked} corrected addresses checked on their page.\n\n")
        f.write(f"## No MX and no A record ({len(no_mx)}) — reports would bounce\n")
        f.writelines(f"- {n}: `{e}`\n" for n, e in no_mx) if no_mx else f.write("- none\n")
        f.write(f"\n## No MX but an A record ({len(a_only)}) — delivered to the host; fine unless it starts bouncing\n")
        f.writelines(f"- {n}: `{e}`\n" for n, e in a_only) if a_only else f.write("- none\n")
        f.write(f"\n## Not confirmed on their page by the automatic check ({len(gone)}) — many sites block automated browsers: check by hand\n")
        f.writelines(f"- {n}: `{e}` — {u}\n" for n, e, u in gone) if gone else f.write("- none\n")
        f.write(f"\n## Look like a person's address — check by hand that the person is still there ({len(personal)})\n")
        f.writelines(f"- {n}: `{e}`\n" for n, e in personal) if personal else f.write("- none\n")
        f.write("\nBy hand: open each listed municipality's contact page and confirm or replace the address "
                "(data/greece/dimoi_emails_corrections.csv, then dimoi-sql.py, a targeted UPDATE of the old address, "
                "dimoi-katalipsi.sql, build-dimoi-data.py).\n")
    print(open(report, encoding="utf-8").read())
    return 1 if no_mx else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
