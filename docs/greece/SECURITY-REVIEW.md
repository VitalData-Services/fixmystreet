# Security review of fixmystreets.gr, 2026-10-29

Read-only review by three independent reviewers (application code, infrastructure, dependencies and repositories).
Nothing was changed on the systems. The full reports are next to this file in `security/`. Private: docs/ is not published.

Counts (the reviewers' own): application code 0 critical, 2 high, 9 medium, 14 low; infrastructure 0 critical, 3 high, 9 medium,
8 low; dependencies and repositories 0 critical, 4 high, about 17 medium, about 13 low. Nothing was found that is remotely
exploitable without further conditions.

## What was checked again by hand

- **Cobrand override (confirmed live):** `/about/terms?_override_cobrand_moniker=default` returns the stock 404 page and the choice stays in the
  visitor's session. Cause: `STAGING_SITE: 1` enables FixMyStreet's development overrides. It switches off the Greece code for that
  visitor (Turnstile checks, the 2FA gate for staff, bad-word and approval holds). Only the visitor's own session is affected.
  Fixed by the flip (`STAGING_SITE: 0`); until then, block `_override_` in nginx.
- **What runs is not the private repo:** the image is `fixmystreet/fixmystreet:stable`, upstream v6.0 of 2024-11-14 on Debian 11.7; the
  private repo is based on upstream master of 2026-10-22. Two files from the newer master are mounted into the v6.0 image.
- **`bin/greece/retention` deletes every token older than 7 days** whatever its kind (confirmed in the code). Upstream alert emails keep their
  unsubscribe links in the same table, so after a week they stop working (to be confirmed against the live table).

## Order of work (proposed)

1. **Before the flip:** `STAGING_SITE: 0`; a backup that is tested (a daily `pg_dump` and the photo volume to another host; no backup job was found on the VM,
   a VM-level one may exist); limit the video upload (Turnstile or a login on `start`, a cap on disk use, the sweep also in a cron).
2. **Soon:** limits in nginx for `/greece/2fa`, `/greece/otp/check`, `/greece/privacy/*`, `/greece/nearby-private` and the photo upload; make the OTP and 2FA try counters atomic;
   fix the open redirect after the 2FA step (`/greece/2fa?r=/\evil.example`); let retention keep alert tokens; stop anyone with Turnstile being able to hide any report
   (`GreecePrivacy`: rate limit, and a token or an email for the report's author).
3. **Platform:** rebuild the image from a pinned upstream commit on a supported base (Debian 12 or later), without the floating `:stable`; upgrade PostgreSQL 13;
   update Catalyst::Plugin::Session (CVE-2025-40924), MapLibre (to a fixed version) and jQuery UI; run the anonymiser and the app as a non-root user; mount code read-only.
4. **Mail:** infra9 relays without authentication for 10.0.0.0/16 and 192.168.0.0/16: narrow `mynetworks` to the hosts that need it.
5. **Smaller:** anonymisation also for `extra->_fields` and `moderation_original_data`; the Content-Security-Policy is report-only (enforce it);
   check the 15 municipal addresses on gmail/yahoo in the public `dimoi/index.json`.

## Not covered

Cloudflare settings (WAF, Access, minimum TLS), VM-level backups, anything that needs a staff session, the production database contents,
which pages load jQuery UI, the 1,689 upstream commits one by one.

## Status, 2026-10-29 (applied after the review, owner: «κάνε τα 2-10»)

Done: nginx block of `_override_` in the query string and limits on 2fa/otp-check/privacy/nearby-private/photo upload; open redirect after 2FA fixed;
OTP and 2FA try counters raised under a row lock; GreecePrivacy ceilings (3 flags per visitor and day, 10 hidings per hour); video upload ceilings
(3 per address, 20 and 3 GB open, 5 GB free disk kept, unfinished uploads swept after 3 h); retention keeps alert tokens; image rebuilt with the
Debian 11 security updates (from archive.debian.org, ImageMagick 6.9.11 deb11u16, OpenSSL, libc) and Catalyst::Plugin::Session 0.44 (rollback tag
`fixmystreets-gr:pre-20261029`); PostgreSQL 13.11 to 16.9 by dump/restore (old volume `fixmystreet-pgdata` and image `fixmystreet-postgres:pre-pg16-13.11`
kept for rollback; pg_hba uses md5 so the old password hashes work, to be re-hashed to scram when the passwords are rotated); infra9 refuses
`@fixmystreets.gr` as sender from every host of 10.0.0.0/16 and 192.168.0.0/16 except the fms VM (`/etc/postfix/fms_sender_clients.cidr`, backup
`main.cf.bak-20261029-fms-sender`); `bin/greece/backup` (pg_dump to /var/backups/fms, 14 days; the cron is the owner's to install).
Not done: image on a current upstream and Debian 12, non-root container and read-only mounts, enforcing the CSP, STAGING_SITE: 0 (the `_override_`
parameters sent in a POST body still reach the app until the flip), the backup copy to another host.

### Debian 12 image (2026-10-29)
The app container now runs on Debian 12.11 (Perl 5.36, ImageMagick 6.9.11 from bookworm, Catalyst::Plugin::Session 0.44), image
`fixmystreets-gr:d12` tagged as `latest`; the same v6.0 application tree. `docker/greece/d12/Dockerfile`. Checked: home, privacy,
terms, reports, auth, sitemap, robots, admin redirect, the Greece controllers compile, database reads, public site 200 through
Cloudflare. Rollback: `docker tag fixmystreets-gr:pre-d12 fixmystreets-gr:latest && docker compose up -d --no-build --force-recreate fixmystreet`
(`pre-20261029` is the older Debian 11 image; Proxmox snapshot `pre-debian12-20261029` of VM 121). The application itself is
still upstream v6.0 (not current upstream).
