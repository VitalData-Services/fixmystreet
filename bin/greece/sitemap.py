#!/usr/bin/env python3
"""Writes web/sitemap.xml to stdout: the home, help and reports pages, and each municipality's
reports page (/reports/<name>, spaces as '+', the address FixMyStreet itself uses and names as
canonical, so search engines meet no redirect), only for municipalities with public reports, with the
date of the latest change as <lastmod>; a municipality's page without any says «noindex»
(templates/web/greece/common_header_tags.html). Reports are not listed yet.

Run on the fms VM from the repository; web/sitemap.xml is a single-file mount, so write it in place:
    python3 bin/greece/sitemap.py > /tmp/sitemap.xml && cat /tmp/sitemap.xml > web/sitemap.xml
"""
import subprocess
import urllib.parse
from xml.sax.saxutils import escape

BASE = 'https://fixmystreets.gr'
PAGES = [('/', 'daily', '1.0'), ('/faq', 'monthly', '0.6'), ('/reports', 'daily', '0.8'), ('/about', 'monthly', '0.5'), ('/about/foreis', 'monthly', '0.4'),
         ('/about/privacy', 'yearly', '0.3'), ('/about/terms', 'yearly', '0.3')]

names = subprocess.run(
    ['docker', 'exec', '-i', 'fixmystreet-postgres-1', 'psql', '-U', 'postgres', '-d', 'fixmystreet', '-At', '-c',
     "SELECT b.name, max(p.lastupdate)::date FROM body b"
     " JOIN problem p ON b.id::text = ANY(string_to_array(p.bodies_str, ','))"
     " WHERE NOT b.deleted AND b.name LIKE 'Δήμος %' AND NOT p.non_public"
     " AND p.state NOT IN ('unconfirmed', 'hidden', 'partial')"
     " GROUP BY b.name ORDER BY b.name"],
    check=True, capture_output=True, text=True).stdout.splitlines()

print('<?xml version="1.0" encoding="UTF-8"?>')
print('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
for path, freq, prio in PAGES:
    print(f'  <url><loc>{escape(BASE + path)}</loc><changefreq>{freq}</changefreq><priority>{prio}</priority></url>')
for line in names:
    name, lastmod = line.split('|')
    path = '/reports/' + urllib.parse.quote(name.replace(' ', '+'), safe='+')
    print(f'  <url><loc>{escape(BASE + path)}</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.5</priority></url>')
print('</urlset>')
