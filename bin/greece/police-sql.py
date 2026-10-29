#!/usr/bin/env python3
"""Write the SQL that routes parking complaints (EV-charging bays, blocked passage) to the police.

Each municipality gets two recipients, as two bodies covering its area with the same category:
  - its Αστυνομικό Τμήμα, when the match is certain (confidence "high" and an e-mail is listed),
    otherwise its Διεύθυνση Αστυνομίας, which forwards citizens' requests to the competent unit;
  - the Τμήμα Τροχαίας picked for it, when there is one with an e-mail.
A body is one police unit, so a unit serving several municipalities covers all their areas.
Only the first body's category asks the questions; the Τροχαία copy has none, so the form shows
them once.

Parking on disabled (ΑμεΑ) bays and ramps, pavements and crossings is recorded on xorisempodia.gr
instead: its category, on the first body only, stops the form and links there, and no report is made.

Usage:
    police-sql.py <dimoi_police.csv> <police_units.csv> <output.sql>

dimoi_police.csv: one row per municipality (data/greece/dimoi_police.csv).
police_units.csv: every unit listed on astynomia.gr, for addresses and phones.
"""
import csv
import json
import re
import sys
import unicodedata

CATEGORY = "Στάθμευση σε φορτιστή EV ή εμπόδιο στη διέλευση"
CATEGORY_AMEA = "Στάθμευση σε ράμπα ή θέση ΑμεΑ, πεζοδρόμιο ή διάβαση"
# Earlier names of the police categories, marked deleted on the police bodies.
OLD_CATEGORIES = ("Στάθμευση σε θέση ΑμεΑ ή φορτιστή EV",)
DOMAINS = ("astynomia.gr", "hellenicpolice.gr")

# MapIt has one area for each of these islands, shared by its municipalities, so a station
# would receive the island's every report; the directorate takes them instead.
SHARED_AREA = {
    "Δήμος Αργοστολίου", "Δήμος Ληξουρίου", "Δήμος Σάμης",
    "Δήμος Βόρειας Κέρκυρας", "Δήμος Κεντρικής Κέρκυρας και Διαποντίων Νήσων", "Δήμος Νότιας Κέρκυρας",
}

# Names astynomia.gr gives in capitals that cannot be rebuilt from the municipality's name.
NAMES = {
    "Α.Τ. ΗΡΑΚΛΕΙΟΥ": "Αστυνομικό Τμήμα Ηρακλείου Αττικής",
    "ΤΜΗΜΑ ΤΡΟΧΑΙΑΣ ΑΣΠΡΟΒΑΛΤΑΣ": "Τμήμα Τροχαίας Ασπροβάλτας",
    "ΤΜΗΜΑ ΤΡΟΧΑΙΑΣ ΘΕΡΜΗΣ": "Τμήμα Τροχαίας Θέρμης",
    "ΤΜΗΜΑ ΤΡΟΧΑΙΑΣ ΛΗΤΗΣ": "Τμήμα Τροχαίας Λητής",
    "ΤΜΗΜΑ ΤΡΟΧΑΙΑΣ ΧΑΛΚΗΔΟΝΟΣ": "Τμήμα Τροχαίας Χαλκηδόνος",
    "ΥΠΟΔ/ΝΣΗ ΤΡΟΧΑΙΑΣ ΑΘΗΝΩΝ": "Υποδιεύθυνση Τροχαίας Αθηνών",
}

QUESTIONS = {
    "email_template": "ev",
    "_fields": [
        {"code": "idiotiki", "variable": "false", "order": 0, "datatype": "string", "required": "false",
         "description": "Η καταγγελία εμφανίζεται στον χάρτη χωρίς όνομα, στοιχεία επικοινωνίας και πινακίδα. Αυτά στέλνονται μόνο στην αρμόδια υπηρεσία της Ελληνικής Αστυνομίας."},
        {"code": "paravasi", "variable": "true", "order": 1, "datatype": "singlevaluelist", "required": "true",
         "description": "Τι συμβαίνει;",
         "values": [
             {"key": "fortistis", "name": "Στάθμευση σε θέση φόρτισης ηλεκτρικών οχημάτων χωρίς φόρτιση"},
             {"key": "eisodos", "name": "Στάθμευση μπροστά σε είσοδο ή έξοδο οχημάτων (γκαράζ)"},
             {"key": "diplo", "name": "Διπλή στάθμευση ή όχημα που κλείνει τον δρόμο"},
             {"key": "stasi", "name": "Στάθμευση σε στάση λεωφορείου"},
             {"key": "empodia", "name": "Παράνομα εμπόδια ή κώνοι από κατάστημα"},
             {"key": "p72", "name": "Αυθαίρετη ή μη εγκεκριμένη διαγράμμιση και πινακίδα P-72"},
         ]},
        # Filled in from the photo where a plate is read (camera.js); the reporter can correct it.
        {"code": "pinakida", "variable": "true", "order": 2, "datatype": "string", "required": "false",
         "description": "Αριθμός κυκλοφορίας (πινακίδα), αν αφορά συγκεκριμένο όχημα"},
        {"code": "arithmos", "variable": "true", "order": 3, "datatype": "string", "required": "false",
         "description": "Αριθμός οδού, αν τον ξέρεις (π.χ. 46)"},
    ],
}
NO_QUESTIONS = {"email_template": "ev"}

# FixMyStreet shows a disable_form field's text instead of the rest of the form and does not take
# the report.
# Its letter (email_template "amea", submit-amea.txt) is for when it is sent to the police again.
XORISEMPODIA = {
    "email_template": "amea",
    "_fields": [
        {"code": "xorisempodia", "variable": "false", "disable_form": "true", "order": 0, "datatype": "string",
         "required": "false",
         "description": "<p>Τη στάθμευση σε ράμπα ή θέση ΑμεΑ, σε πεζοδρόμιο ή σε διάβαση την καταγράφει το "
                        "<strong>Χωρίς Εμπόδια</strong>: χωρίς λογαριασμό και χωρίς φωτογραφία, και σου ετοιμάζει "
                        "SMS για το 100, που το στέλνεις εσύ από το κινητό σου.</p>"
                        "<p><a class=\"btn btn--primary\" href=\"https://xorisempodia.gr/reports/new\" "
                        "target=\"_blank\" rel=\"noopener\">Κατάγραψέ το στο xorisempodia.gr</a></p>"},
    ],
}

BASIS = {
    "at": "",
    "directorate": "Αντί για Αστυνομικό Τμήμα, όπου η αντιστοίχιση δεν είναι βέβαιη· δέχεται αιτήματα πολιτών και τα προωθεί στην αρμόδια υπηρεσία (ΕΛ.ΑΣ., 17/06/2020).",
    "tt": "Δεύτερος παραλήπτης. Η περιοχή κάθε Τμήματος Τροχαίας δεν δημοσιεύεται· επιλέχθηκε από τη Διεύθυνση και την απόσταση.",
}

SHOUTING = re.compile(r"[Α-ΩΪΫ]{4,}")
AT_PREFIX = re.compile(r"^(?:(?P<ord>[Α-Ω])['΄’ʹ]\s+)?(?:Α\.\s*Τ\.|ΑΣΤΥΝΟΜΙΚΟ ΤΜΗΜΑ|ΑΣΤΥΝ\.\s*ΤΜΗΜΑ)\s*(?P<place>.+)$")


def plain(s):
    """Capitals without accents, dashes or spaces, for comparing names."""
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
    return re.sub(r"[\s\-–—]+", "", s.upper())


def tidy(name):
    name = re.sub(r"\s+", " ", name).strip()
    return re.sub(r"(?<=\b[Α-Ω])[΄’ʹ]", "'", name)


def station_name(row):
    """The station's name in normal case; astynomia.gr writes some in capitals."""
    name = tidy(row["at_name"])
    if name in NAMES:
        return NAMES[name]
    if name.startswith("Α.Τ. ") and not SHOUTING.search(name):
        return "Αστυνομικό Τμήμα " + name[5:]
    if not SHOUTING.search(name):
        return name
    m = AT_PREFIX.match(name)
    place = row["name_el"].removeprefix("Δήμος ")
    if not m or plain(m["place"]) != plain(place):
        sys.exit(f"cannot rebuild the name {name!r} ({row['name_el']}); add it to NAMES")
    return (m["ord"] + "' " if m["ord"] else "") + "Αστυνομικό Τμήμα " + place


def unit_name(name):
    name = tidy(name)
    if name in NAMES:
        return NAMES[name]
    if SHOUTING.search(name):
        sys.exit(f"name in capitals {name!r}; add it to NAMES")
    return name


def load_units(path):
    """{e-mail: (address, phone)} from police_units.csv."""
    units = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            phones = [p.split(": ", 1) for p in row["phones"].split("; ") if ": " in p]
            phone = next((f"{label}: {number}" for want in ("Αξιωματικός Υπηρεσίας", "Τηλεφωνική γραμμή εξυπηρέτησης", "Τηλεφωνικό Κέντρο")
                          for label, number in phones if label == want), "")
            if not phone and phones:
                phone = ": ".join(phones[0])
            for item in row["emails"].split("; "):
                email = item.split(": ", 1)[-1].strip().lower()
                if email:
                    units.setdefault(email, (row["address"].strip(), phone))
    return units


def check_email(email, where):
    if not re.fullmatch(r"[a-z0-9._-]+@[a-z0-9.-]+", email) or email.split("@")[1] not in DOMAINS:
        sys.exit(f"unexpected e-mail {email!r} for {where}")


def sql(s):
    return "'" + s.replace("'", "''") + "'"


def main(dimoi_path, units_path, out_path):
    units = load_units(units_path)
    bodies = {}   # name -> {email, kind}
    areas = []    # (body name, municipality)

    def add(name, email, kind, dimos):
        email = email.strip().lower()
        check_email(email, f"{name} ({dimos})")
        if name.startswith("Δήμος"):
            sys.exit(f"{name} would be tagged as a police body")
        body = bodies.setdefault(name, {"email": email, "kind": kind})
        if body["email"] != email or body["kind"] != kind:
            sys.exit(f"{name} has two e-mails or roles: {body['email']} / {email}")
        areas.append((name, dimos))

    with open(dimoi_path, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        dimos = row["name_el"]
        if row["confidence"] == "high" and row["at_email"] and dimos not in SHARED_AREA:
            add(station_name(row), row["at_email"], "at", dimos)
        else:
            add(unit_name(row["directorate"]), row["directorate_email"], "directorate", dimos)
        if row["tt_email"]:
            add(unit_name(row["tt_name"]), row["tt_email"], "tt", dimos)

    emails = {}
    for name, body in bodies.items():
        if emails.setdefault(body["email"], name) != name:
            sys.exit(f"{body['email']} belongs to both {emails[body['email']]} and {name}")

    # Stations and directorates first, so that they get the lower ids and are named first.
    order = sorted(bodies, key=lambda n: (bodies[n]["kind"] == "tt", n))
    body_values = []
    for sort, name in enumerate(order):
        body = bodies[name]
        address, phone = units.get(body["email"], ("", ""))
        note = " · ".join(p for p in (name, address, phone, BASIS[body["kind"]]) if p)
        body_values.append(f"  ({sql(name)}, {sql(body['email'])}, {sql(note)}, {'false' if body['kind'] == 'tt' else 'true'}, {sort})")
    area_values = [f"  ({sql(name)}, {sql(dimos)})" for name, dimos in areas]

    kinds = {k: sum(1 for b in bodies.values() if b["kind"] == k) for k in BASIS}
    with open(out_path, "w") as out:
        out.write(f"""-- Police bodies for parking complaints (EV-charging bays, blocked passage), all municipalities.
-- Generated by bin/greece/police-sql.py from data/greece/dimoi_police.csv and
-- data/greece/police_units.csv (astynomia.gr/epikoinonia, read 2026-10-24); do not edit by hand.
-- {kinds['at']} stations, {kinds['directorate']} directorates and {kinds['tt']} traffic units for {len(rows)} municipalities.
-- Each municipality's area is covered by a station or directorate body and, where one is known,
-- a Τμήμα Τροχαίας body, both with the category below, so a report is sent to both in one email.
-- The category is public since 2026-10-26, without personal details (Greece.pm greece_public_complaint:
-- anonymous, plates masked in the description); the email is the
-- complaint letter in submit-ev.txt/html, chosen by email_template.
-- The station or directorate body also has the ΑμεΑ category, which only links to xorisempodia.gr
-- (disable_form): FixMyStreet takes no report in it, so its e-mail is never used.
-- Police bodies are tagged greece_police in body.extra. Re-running replaces their areas with the
-- ones below, and their category is marked deleted where they are no longer listed.
BEGIN;
CREATE TEMP TABLE police_bodies (name text, email text, note text, questions boolean, sort int) ON COMMIT DROP;
INSERT INTO police_bodies VALUES
{(","+chr(10)).join(body_values)};

CREATE TEMP TABLE police_areas (name text, dimos text) ON COMMIT DROP;
INSERT INTO police_areas VALUES
{(","+chr(10)).join(area_values)};

DO $$
DECLARE missing text;
BEGIN
  SELECT string_agg(DISTINCT pa.dimos, ', ') INTO missing FROM police_areas pa
   WHERE NOT EXISTS (SELECT 1 FROM body d JOIN body_areas a ON a.body_id = d.id WHERE d.name = pa.dimos AND NOT d.deleted);
  IF missing IS NOT NULL THEN RAISE EXCEPTION 'municipalities without a body or area: %', missing; END IF;
END $$;

INSERT INTO body (name)
SELECT pb.name FROM police_bodies pb
 WHERE NOT EXISTS (SELECT 1 FROM body b WHERE b.name = pb.name AND NOT b.deleted)
 ORDER BY pb.sort;

UPDATE body SET extra = coalesce(extra, '{{}}'::jsonb) || '{{"greece_police": 1}}'::jsonb
 WHERE NOT deleted AND name IN (SELECT name FROM police_bodies);

CREATE TEMP TABLE police_body_areas ON COMMIT DROP AS
SELECT DISTINCT p.id AS body_id, a.area_id
  FROM police_areas pa
  JOIN body p ON p.name = pa.name AND NOT p.deleted
  JOIN body d ON d.name = pa.dimos AND NOT d.deleted
  JOIN body_areas a ON a.body_id = d.id;

DELETE FROM body_areas ba
 WHERE ba.body_id IN (SELECT id FROM body WHERE extra ? 'greece_police')
   AND NOT EXISTS (SELECT 1 FROM police_body_areas x WHERE x.body_id = ba.body_id AND x.area_id = ba.area_id);

INSERT INTO body_areas (body_id, area_id)
SELECT body_id, area_id FROM police_body_areas
ON CONFLICT (body_id, area_id) DO NOTHING;

INSERT INTO contacts (body_id, category, email, state, editor, whenedited, note, non_public, extra)
SELECT b.id, {sql(CATEGORY)}, pb.email, 'confirmed', 'import', now(), pb.note, false,
       CASE WHEN pb.questions THEN {sql(json.dumps(QUESTIONS, ensure_ascii=False))}::jsonb
            ELSE {sql(json.dumps(NO_QUESTIONS, ensure_ascii=False))}::jsonb END
  FROM police_bodies pb JOIN body b ON b.name = pb.name AND NOT b.deleted
ON CONFLICT (body_id, category) DO UPDATE
  SET email = EXCLUDED.email, note = EXCLUDED.note, non_public = EXCLUDED.non_public, extra = EXCLUDED.extra,
      state = 'confirmed', editor = 'import', whenedited = now();

INSERT INTO contacts (body_id, category, email, state, editor, whenedited, note, non_public, extra)
SELECT b.id, {sql(CATEGORY_AMEA)}, pb.email, 'confirmed', 'import', now(), 'Μόνο σύνδεσμος προς το xorisempodia.gr.', true,
       {sql(json.dumps(XORISEMPODIA, ensure_ascii=False))}::jsonb
  FROM police_bodies pb JOIN body b ON b.name = pb.name AND NOT b.deleted
 WHERE pb.questions
ON CONFLICT (body_id, category) DO UPDATE
  SET email = EXCLUDED.email, note = EXCLUDED.note, non_public = EXCLUDED.non_public, extra = EXCLUDED.extra,
      state = 'confirmed', editor = 'import', whenedited = now();

UPDATE contacts SET state = 'deleted', editor = 'import', whenedited = now()
 WHERE category IN ({", ".join(sql(c) for c in OLD_CATEGORIES)}) AND state <> 'deleted'
   AND body_id IN (SELECT id FROM body WHERE extra ? 'greece_police');

UPDATE contacts SET state = 'deleted', editor = 'import', whenedited = now()
 WHERE category = {sql(CATEGORY_AMEA)} AND state <> 'deleted'
   AND body_id IN (SELECT id FROM body WHERE extra ? 'greece_police')
   AND body_id NOT IN (SELECT b.id FROM police_bodies pb JOIN body b ON b.name = pb.name AND NOT b.deleted WHERE pb.questions);

UPDATE contacts SET state = 'deleted', editor = 'import', whenedited = now()
 WHERE category = {sql(CATEGORY)} AND state <> 'deleted'
   AND body_id IN (SELECT id FROM body WHERE extra ? 'greece_police')
   AND body_id NOT IN (SELECT b.id FROM police_bodies pb JOIN body b ON b.name = pb.name AND NOT b.deleted);
COMMIT;
""")
    print(f"{len(bodies)} bodies ({kinds}), {len(areas)} links written to {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
