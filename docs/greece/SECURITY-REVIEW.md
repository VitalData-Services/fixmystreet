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
