# fixmystreets.gr roadmap

Private (docs/ is not published to the public fork). Owner decisions are dated. Newest first inside each section.

## Next: the request desk («Γραφείο αιτημάτων»)

**Goal (owner, 2026-10-28):** answering a citizen's request must be very simple. Today the admin handbook
(`/admin/greece/handbook`) says what to do; the desk does it with a few clicks and never lets a deadline pass.

Requests it covers: access/copy (Art. 15), erasure (Art. 17), rectification (Art. 16), objection/restriction
(Art. 21/18), «recall what you sent to the municipality/police», privacy flag (hide a report), content notice
(abuse/DSA). All of them have a legal deadline of one month, or less.

### What the admin sees

- `/admin/greece/requests`: one list, oldest due date first. A request is a row with the citizen's email, the kind,
  the date it arrived, the **due date** (arrival + 1 month; +2 months only with a written reason), the status
  (new / waiting for the citizen / ready to answer / answered) and a colour: green > 7 days, amber ≤ 7, red overdue.
- **New request** takes 10 seconds: paste the email address, pick the kind, save. The due date is filled in.
- Each request has one page with the same four buttons whatever the kind:
  1. **Check the person.** Sends a one-time link to the account's own email; the request is marked verified when
     they click it (no ID copies).
  2. **Do it.** The kind's action, with a preview first:
     - access: runs `dsar export`, shows what is in the file, offers the download;
     - erasure: runs `dsar erase` as a dry run, lists what stays (reports without name) and what needs a look
       (photos, videos), then `--commit` on confirmation;
     - rectification: opens the report or account edit;
     - privacy flag / notice: opens the report in the hide/restore screen.
  3. **Reply.** The reply text of the handbook, with the report number, dates and names already filled in, to
     edit and send from the site's contact address (or copy).
  4. **Done.** Records who, when, what was sent. The request stays as a record.
- Everything the admin does on a request is written to a short log line (who, what, when; no personal data).

### Make it hard to miss a deadline

- A daily email at 08:00 to the contact address: requests due in 7 days or less, and overdue ones.
- Requests arrive without typing where possible: the privacy-flag button and the contact form (subject «Αίτημα
  δικαιωμάτων») create a row by themselves.

### Phases

1. **Small (about a day):** the table, the list with deadlines and colours, «new request», the daily email, the
   handbook texts filled in. No automation of the actions yet.
2. **One-click actions:** export and erase with preview, report hide/restore from the request page.
3. **Intake and verification:** requests from the privacy button and the contact form, the one-time link.

### Needs before building

- A table in the database (`greece_request`: id, kind, email, received_at, due_at, extended_reason, status,
  verified_at, answered_at, handled_by, note) and a migration.
- A retention rule for the table: keep the record of a request for 3 years (accountability), then delete the
  row. Add it to `bin/greece/retention`, the privacy page §8 and the RoPA.
- Privacy page and RoPA: «requests we receive» as a processing activity; DPIA: one line.
- Superusers only, CSRF, behind the second sign-in step like `/admin/greece/approve`.

## Later

- Email change for an account (needs a confirmation to the new address).
- Postal code in the address of a report.
- Automated tests for the Greece controllers (none today).
- Translations that live in the `.po`: «Αναφορά δημοσίευσης» (report abuse), «Και εμείς θα το στείλουμε…».
  The `.mo` is not in git: needs a rebuild step in the image.
- Pin the base image (floating `:stable` today) and keep `.mo` in the build.
- Postgres 13 is end of life: plan the upgrade.
- Read the SPF/DKIM/DMARC reports for fixmystreets.gr; check that DMARC is published.

## Decided not to do

- Open data publishing (2026-10-28). The code is open source (AGPL); the data is not offered as open data.
- AI features (category suggestion, moderation help) (2026-10-28).
- The pre-flip admin items stay as they are (2026-10-28): rotate the bounces@/falcon@ passwords, legal form and
  roles agreement, someone reading falcon@ daily, `pg_dump` before the flip, Veeam exclusion of
  `/var/lib/fms-originals`. They are recorded as risks, not tasks.

## Done today (2026-10-28), for orientation

Retention (anonymise after 24 months, inactive accounts, edit history 3 months), author edit of reports, account
page, terms cookie, minimal form notes, complaints always anonymous, collapsible municipality card, deeper blue
and fixed green (WCAG AA), logo rebuilt from the 2172 px original, map credit behind a button, relay via infra9,
admin handbook.
