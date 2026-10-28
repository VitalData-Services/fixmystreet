# Legitimate Interests Assessment (LIA): fixmystreets.gr

Version 1, 2026-10-28. Internal document, not published (the privacy page, section 3, states the conclusion). It records that the assessment was made, as Art. 5(2) GDPR requires. Controller: VitalData Services, Περραιβού 19, Χαϊδάρι. To be reviewed once a year and when a purpose or a data flow changes, together with the DPIA (`dpia.md`) and the RoPA (`ropa.md`).

Each assessment follows the three questions of the Article 29 Working Party and the EDPB: is the interest legitimate (purpose test), is the processing needed for it (necessity test), and do the individual's interests override it (balancing test).

## 1. Sending reports to the municipalities

| Test | Assessment |
|---|---|
| Purpose | Getting a problem in public space (pothole, broken pavement, blocked ramp, light out) to the service that can fix it. It serves the reporter, other residents and the municipality. The interest is lawful and concrete. |
| Necessity | The report has to reach the right service to be useful; email to the service's address is the least intrusive way that works. Only what the service needs is sent: point, category, description, photos, date, and the name and phone the reporter chose to give. The reporter's email is sent only when the reporter has confirmed it with the emailed code. Reports go in batches after an administrator has checked them (four times a day), not one by one. |
| Balancing | The reporter put the report there on purpose and expects it to reach the service. The data is mostly about a place, not a person. Name and phone are optional and shown to the service only if given. Reasonable expectation: high. Impact on the individual: low. Safeguard: a person who does not want to be identified reports without a name when a photo is attached. |
| Outcome | The interest prevails. Legal basis: Art. 6(1)(f). A municipality that receives a report is a separate controller from then on. |

## 2. Showing the point and the description publicly

| Test | Assessment |
|---|---|
| Purpose | A public record lets neighbours see what has been reported, avoids duplicate reports, and lets anyone check what is fixed. This is the transparency a civic reporting service exists for. |
| Necessity | A map needs the point. The description explains the problem. The name, email and phone are not shown (the name only if the reporter ticks the box, which is consent under Art. 6(1)(a)). Plates in descriptions are replaced by `***`. |
| Balancing | The data published is limited to the point, the category, the description and the date. The main risk is that an exact point and a description identify a household or a person (a report about a neighbour's property). Mitigations: reports are anonymous by default; the description rules in the Terms forbid third parties' names; a report can be hidden at once by anyone from its page (`/greece/privacy/<id>`), and removed or anonymised on request. Residual risk: medium, accepted. |
| Outcome | The interest prevails with those safeguards. Art. 6(1)(f). The right to object (Art. 21) is honoured by hiding or anonymising. |

## 3. Publishing photos

| Test | Assessment |
|---|---|
| Purpose | A photo shows the problem far better than words and lets the service find it. |
| Necessity | A photo is needed for most categories; it is the reason a report with a photo may be anonymous. Faces and number plates are not needed, so every uploaded photo goes through the anonymiser before it is stored (blurred in the public copy). |
| Balancing | People and vehicles can appear by accident. The blurring makes the public copy mostly free of identifiable people: in a test on 7 street photos, all 7 visible plates were found and blurred; people far away in a street scene stayed unblurred because they are not identifiable at that size. The test is small and the photos were clean, so the assessment keeps a residual risk (low to medium). Mitigations: nudity detection and moderation, instant hiding on a privacy flag, the Terms ask the user to check the result. |
| Outcome | The interest prevails with those safeguards. Art. 6(1)(f). Reviewed when the anonymiser changes. |

## 4. Passing photos with readable plates to the police

| Test | Assessment |
|---|---|
| Purpose | Parking on ramps and disabled bays, and blocking of charging bays, are offences the Hellenic Police enforce. Without the plate the report cannot be acted on. |
| Necessity | The plate is needed only for these categories and only for the police. The plate text may be filled in from the photo; the reporter can correct it. The readable copy goes only in the police letter; the public copy is blurred, and the plate in the public text is replaced by `***`. |
| Balancing | A plate identifies the vehicle's keeper. The people concerned are alleged offenders, and the processing is limited to the report that identifies the offence. The police copy is deleted as soon as the letter is sent, and in any case after 30 days (`bin/greece/purge-originals`). The reporter takes responsibility for the accuracy of the report (Terms). Risk of a wrong plate or a false report: the police assess it; the operator does not decide anything about the vehicle's keeper. Impact on the individual: medium; expectation: a driver parked illegally can expect to be reported. |
| Outcome | The interest prevails for these categories only. Art. 6(1)(f). Not extended to other categories. |

## 5. Preventing spam and abuse

| Test | Assessment |
|---|---|
| Purpose | Keeping the service usable and safe: stopping automated and abusive submissions, protecting reporters' email addresses and the municipalities' mailboxes from flooding. |
| Necessity | A challenge on forms (Cloudflare Turnstile, which sees the visitor's browser and IP), rate limits in nginx, server logs with IP address, browser and time for security and fixing errors, a code sent by email to confirm an address. Each is the usual, proportionate measure; none builds a profile of the visitor. Analytics were removed. |
| Balancing | The data is technical, kept for a short time (logs rotate at 3 x 10 MB per container; email codes live 15 minutes and are purged after 7 days). People expect such checks on a public form. Impact: low. Cloudflare acts as a processor under its data processing addendum, with the Standard Contractual Clauses for transfers outside the EEA. |
| Outcome | The interest prevails. Art. 6(1)(f). |

## Review record

| Date | Who | What changed |
|---|---|---|
| 2026-10-28 | Drafted for the controller | First version |
