# FixMyStreets Ελλάδα — Docker

`docker-compose.yml` builds this image instead of using `fixmystreet/fixmystreet:stable` directly.
The only change is that it generates the `el_GR.UTF-8` system locale: without it, `setlocale()`
fails and every string falls back to English, even with a complete Greek `.mo` in place.

## Greek translation

The translation is mounted from `locale/el_GR.UTF-8/LC_MESSAGES`. The compiled `.mo` is
gitignored, so compile it after every change to the `.po` and restart the app container:

    docker run --rm -v "$PWD/locale/el_GR.UTF-8/LC_MESSAGES:/l" fixmystreet/fixmystreet:stable \
      msgfmt -c -o /l/FixMyStreet.mo /l/FixMyStreet.po
    docker compose restart fixmystreet

## Secrets

`.env` (gitignored) holds `FMS_SUPERUSER_PASSWORD=...`. `docker compose` refuses to start without it.

## Greece cobrand

`ALLOWED_COBRANDS: [ greece ]` selects `perllib/FixMyStreet/Cobrand/Greece.pm`, which inherits the
Default cobrand and reuses its CSS (`asset_moniker` is `default`). `docker-compose.yml` mounts the
module, `templates/web/greece` and `web/cobrands/greece` into the app container.

The homepage shows a location minimap above the address search
(`templates/web/greece/around/_location_minimap.html`, `web/cobrands/greece/minimap.js`):

- MapLibre GL 4.7.1 (vendored, BSD-3-Clause) with the OpenFreeMap "positron" style, with building
  layers removed and rotation/pitch disabled.
- It locates the visitor on request, or straight away if geolocation permission was already
  granted. "Αναφορά εδώ" opens `/report/new` at the map centre.
- It outlines the municipality under the pin and shows its contact details from
  `web/cobrands/greece/dimoi/`: `index.json` plus one boundary file per OSM relation. Rebuild them
  with `bin/greece/build-dimoi-data.py` when contact details change. The municipality lookup runs in
  the browser against these files; only the map tiles come from a third party (OpenFreeMap), which
  therefore sees the area being viewed, as with any web map.

## Caching in front of the site

If a CDN sits in front of the site, it must keep the query string in the cache key. FixMyStreet
versions static assets as `file.js?<md5>`, so a cache that ignores query strings keeps serving old
files after an update.

## Report reference

Every report gets a public reference `DDMMYYYY-N`: the local (`TIME_ZONE`) date it was created
and its position among all reports created that day, e.g. `24102026-3`. It is computed on the fly
(`FixMyStreet::DB::Result::Problem::greece_ref` in `Greece.pm`), shown on the report page and in the
email to the municipality, and accepted in the search box, alongside `ref: <id>`. A bare number
stays a place search, because Greek postcodes are five digits.

## Emails to municipalities

`templates/email/greece/submit.txt` and `submit.html` are the Greek versions of the report email
(formal register), and include the reference. `signature.txt` and `site-name.txt` apply to every
email. Other emails still fall back to the English `templates/email/default`.

## Municipality categories

Each municipality's report categories and receiving addresses are kept as idempotent SQL in
`data/greece/contacts/<municipality>.sql`, with the source page noted. Contact details shown on the
minimap card come from `data/greece/dimoi_contacts_manual.csv`, which overrides the base CSV in
`bin/greece/build-dimoi-data.py`. A category named `Άλλα` (the translation of "Other") is always
listed last.
