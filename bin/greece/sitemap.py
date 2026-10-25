#!/usr/bin/env python3
"""Writes web/sitemap.xml to stdout: the home, help and reports pages, and each municipality's
reports page (/reports/<name>, spaces as '+', the address FixMyStreet itself uses and names as
canonical, so search engines meet no redirect). Reports are not listed yet.

Run on the fms VM from the repository; web/sitemap.xml is a single-file mount, so write it in place:
    python3 bin/greece/sitemap.py > /tmp/sitemap.xml && cat /tmp/sitemap.xml > web/sitemap.xml
"""
import subprocess
import urllib.parse
from xml.sax.saxutils import escape

BASE = 'https://fixmystreets.gr'
PAGES = [('/', 'daily', '1.0'), ('/faq', 'monthly', '0.6'), ('/reports', 'daily', '0.8'), ('/about/foreis', 'monthly', '0.4')]

names = subprocess.run(
    ['docker', 'exec', '-i', 'fixmystreet-postgres-1', 'psql', '-U', 'postgres', '-d', 'fixmystreet', '-At', '-c',
     "SELECT name FROM body WHERE NOT deleted AND name LIKE 'Δήμος %' ORDER BY name"],
    check=True, capture_output=True, text=True).stdout.splitlines()

print('<?xml version="1.0" encoding="UTF-8"?>')
print('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
for path, freq, prio in PAGES:
    print(f'  <url><loc>{escape(BASE + path)}</loc><changefreq>{freq}</changefreq><priority>{prio}</priority></url>')
for name in names:
    path = '/reports/' + urllib.parse.quote(name.replace(' ', '+'), safe='+')
    print(f'  <url><loc>{escape(BASE + path)}</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>')
print('</urlset>')
