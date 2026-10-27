# Data Protection Impact Assessment: fixmystreets.gr

Version 3, 2026-10-27. Internal document, not published. Reviewed by three independent LLM reviewers (qwen-local, deepseek-v4-flash, gpt-oss-120b) and checked against the deployed code by Claude. Pending: owner approval and, if wanted, a lawyer's reading.

**Controller:** the operator of fixmystreets.gr, contact falcon@fixmystreets.gr. [Still to add: the name of the legal person or the named people behind it, and a postal address. A contact email alone does not identify the controller (Art. 13(1)(a), Art. 30(1)(a)).]
**Hosting:** the operator's own server (Veeam-backed hypervisor), reached through a Cloudflare Tunnel. Mail leaves through the operator's own relay.
**Processors and recipients outside the operator:** Cloudflare (tunnel, CDN, Turnstile), Google (only for Google sign-in), Komoot Photon (address text), OpenStreetMap Nominatim (coordinates), mySociety MapIt (boundaries, no personal data sent).
**Why a DPIA:** the service combines systematic collection of precise location, photographs of public space (faces and vehicle plates of passers-by) and optional video, and publishes part of it. That matches several criteria of the WP248 guidance and the Hellenic Data Protection Authority's list under Art. 35(4) (location and image data, and data about third parties who are not told). A DPIA is the safe course even if a single criterion would not require it.

## 1. The processing

| | |
|---|---|
| Purpose | Let citizens report problems in public space so the responsible municipality or the Hellenic Police can act, and show the reports on a public map. |
| Data subjects | Reporters; people who appear in photos or videos (faces, plates); staff of municipalities, police and the operator who hold accounts. |
| Data | Point on the map and derived address, category, answers to category questions, description, photos, optional video (up to 45 s), optional name, email, phone; for accounts email, name, password hash or the Google identifier; IP, browser and times in server logs. |
| Name rule | A report with a photo may be anonymous. A report without a photo needs a name of at least 4 characters. Email and phone are optional; email is required only if the reporter asks to show their name. |
| Recipients | The responsible municipality's service address (about 2 637 confirmed addresses; 26 municipalities have per-service addresses and the central address in Cc), the Hellenic Police for parking and charger categories. After sending, the receiving authority is a separate controller. |
| Public | Point, category, description, blurred photos, date, updates. Never email or phone; the name only if the reporter chose it. Complaints to the police are shown without name and with plates in the text replaced by `***`. |
| Retention | Reports are kept (historical statistics). Videos 180 days, unclaimed uploads 1 day, police photo copies until sent and at most 30 days, tokens 7 days, unconfirmed reports and updates 14 days, disabled or unconfirmed alerts 90 days, sessions until they expire. Mail logs rotate weekly. Contact messages and the `bounces@` mailbox: see section 4. |
| Legal bases | Forwarding and publishing a report: legitimate interest, Art. 6(1)(f) (see the balancing test below). Showing the reporter's name: consent, Art. 6(1)(a), a separate checkbox. Account, update emails, Google sign-in: Art. 6(1)(b), the service the user asks for. Email confirmation code and bot protection, statistics, security logs: Art. 6(1)(f). |

## 2. Legitimate interest: balancing test for the public map

- **Interest:** a public, searchable record of problems in public space lets residents, municipalities and the press see what is reported and what is fixed. This is a legitimate and widely recognised interest.
- **Necessity:** the exact point is needed to route the report and to let others recognise the same problem. A report without a photo is limited to a name-identified reporter, which discourages invented reports. Name, email and phone are not published unless the reporter asks.
- **Balancing:** the reporter's identity stays hidden by default. The remaining personal data is incidental: faces and plates are blurred before the photo is stored, and the sharper copy for the police is deleted once the letter is sent. The residual risk is that a precise point plus a photo identifies a household when the problem is on private property or at a home. Mitigations and the remaining risk are in section 3. Objection under Art. 21 is honoured by `bin/greece/dsar erase` and by hiding the report.

## 3. Risks and measures

| # | Risk | Likelihood / impact | Measures in place | Residual |
|---|---|---|---|---|
| 1 | A reporter or a resident is re-identified from point, photo and time | Medium / Medium | Anonymous by default; name public only on opt-in; email and phone never shown; faces and plates blurred before storing | Medium |
| 2 | A plate or face stays readable | Medium / High | The anonymiser runs on every photo from the report and update forms, which are converted to JPEG before storage (the fallback in `PhotoSet` stores the original only if conversion itself fails). Police copy deleted when sent, at most after 30 days (`bin/greece/purge-originals`). Plates in descriptions masked on the public page | Low to medium |
| 3 | A plate read by OCR is stored | Medium / Medium | The raw OCR text lives only in the upload request. If the reporter accepts it, the plate is saved in the answer `pinakida` in `problem.extra` and goes to the police letter; it is not shown publicly | Low |
| 4 | Nudity or other unsuitable images are published | Low / High | NudeNet check on every JPEG; flagged reports are held for a moderator; bad-word moderation | Low |
| 5 | Scraping or misuse of the public map | Medium / Medium | Per-endpoint rate limits in nginx (votes, OTP, video upload, address search, MapIt, form posts) and Turnstile on forms; no limit on plain map or listing views; empty municipality pages are `noindex` | Medium |
| 6 | Weak sign-in or takeover | Low / Medium | Email confirmation code (15 minutes, 5 tries, rate limited), passwords hashed, Google sign-in verified with signed state and nonce, staff and superuser accounts need a second step (code by email), staff cannot use social sign-in | Low |
| 7 | Dependence on Cloudflare (it carries all traffic) | Medium / Medium | HTTPS only; the tunnel avoids open inbound ports; Turnstile data limited to the challenge | Medium until the DPA is confirmed |
| 8 | Loss or exposure of the server or backups | Low / High | Veeam backups on the hypervisor; access limited to administrators; security headers; Docker logs rotated at 3 x 10 MB | Low |
| 9 | Email not delivered or sent to a wrong address | Medium / Low | SPF, DKIM and DMARC (`p=reject`) on the domain; delivery tracked per report (`bin/greece/mail-delivery`); bounces read twice a day | Low |

Other points assessed:
- **Third parties in photos and videos.** Passers-by and vehicles appear incidentally. They are data subjects (Art. 14, with the exemption for disproportionate effort in Art. 14(5)(b), supported by the privacy page's note that plates and faces are blurred and by the instruction not to write third-party names).
- **Special categories (Art. 9).** The service does not ask for health, sex life or similar data. Photos of a disabled parking bay concern a parking violation, not the health of a person, and the category does not record who is disabled. Photos can still show injured people or nudity by accident; those are caught by the nudity check and moderation. If a moderator sees such content it is hidden. This conclusion is the operator's and should be confirmed.
- **Cookies (ePrivacy, Greek law 3471/2006).** Login session, Turnstile and the saved report draft are strictly necessary. The `gr_voter` cookie holds a random id for 90 days (shortened from two years on 2026-10-27) so a vote counts once. It is used only for the vote the user asks for.
- **Digital Services Act (Regulation 2022/2065).** The service hosts content from users. To check: a published point of contact, a way to notify illegal content, and the exemptions for micro and small enterprises. Not verified against the text here.

## 4. Open measures

| Measure | Owner action |
|---|---|
| Add the controller's name and postal address next to the contact email (falcon@fixmystreets.gr) on the privacy page and in the RoPA | Owner |
| Data processing terms with Cloudflare (self-serve DPA) | Owner signs |
| Contact messages and the `bounces@` mailbox: define retention (proposal: contact messages 12 months, delivery reports 90 days) and how to erase them. They are emails, so `bin/greece/dsar` does not reach them | Owner decides |
| Delete `nsfw/*.json` metadata older than 30 days (today `purge-originals` ignores them; the folder is empty) | Claude, small change |
| Plausible retention period | Owner |
| Restore test of the Veeam backups, once a year | Owner |
| Rate limit for plain map and listing views | Optional |
| Check the Digital Services Act duties | Owner or lawyer |

## 5. Conclusion

With the measures above the processing is necessary and proportionate for a small service in the public interest, and the overall residual risk is **medium**. No prior consultation with the Authority under Art. 36 is needed, because no high residual risk remains once the open measures are done. Review this document when a new data flow is added (for example a connection to another reporting platform), after any security incident, and at least once a year.
