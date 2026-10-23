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
