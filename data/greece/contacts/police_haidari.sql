-- Αστυνομικό Τμήμα Χαϊδαρίου: receives complaints about disabled (ΑμεΑ) and EV-charging bays in
-- Δήμος Χαϊδαρίου, as its own body covering the municipality's area.
-- Source: https://www.astynomia.gr/epikoinonia/genikes-astynomikes-diefthynseis/g-a-d-attikis/geniki-astynomiki-diefthynsi-attikis/
-- (read 2026-10-24).
-- The category is private (non_public) because a complaint can name a vehicle; the email is the
-- complaint letter in submit-amea.txt/html, chosen by email_template.
BEGIN;
INSERT INTO body (name)
SELECT 'Αστυνομικό Τμήμα Χαϊδαρίου'
WHERE NOT EXISTS (SELECT 1 FROM body WHERE name = 'Αστυνομικό Τμήμα Χαϊδαρίου');

INSERT INTO body_areas (body_id, area_id)
SELECT p.id, a.area_id
FROM body p, body d JOIN body_areas a ON a.body_id = d.id
WHERE p.name = 'Αστυνομικό Τμήμα Χαϊδαρίου' AND d.name = 'Δήμος Χαϊδαρίου'
  AND NOT EXISTS (SELECT 1 FROM body_areas x WHERE x.body_id = p.id AND x.area_id = a.area_id);

INSERT INTO contacts (body_id, category, email, state, editor, whenedited, note, non_public, extra)
SELECT b.id, 'Στάθμευση σε θέση ΑμεΑ ή φορτιστή EV', 'atchaidariou@astynomia.gr', 'confirmed', 'import', now(),
       'Α.Τ. Χαϊδαρίου, Αγ. Γρηγορούσσης 3, 124 61 Χαϊδάρι · Αξιωματικός Υπηρεσίας 210 5819226', true,
       '{
         "email_template": "amea",
         "_fields": [
           {"code": "idiotiki", "variable": "false", "order": 0, "datatype": "string", "required": "false",
            "description": "Οι αναφορές αυτής της κατηγορίας δεν δημοσιεύονται στον ιστότοπο. Στέλνονται, με το όνομα και τα στοιχεία επικοινωνίας σας, μόνο στην αρμόδια υπηρεσία της Ελληνικής Αστυνομίας."},
           {"code": "paravasi", "variable": "true", "order": 1, "datatype": "singlevaluelist", "required": "true",
            "description": "Τι συμβαίνει;",
            "values": [
              {"key": "xoris_karta", "name": "Στάθμευση σε θέση ΑμεΑ χωρίς την ειδική Μπλε Κάρτα"},
              {"key": "fortistis", "name": "Στάθμευση σε θέση φόρτισης ηλεκτρικών οχημάτων χωρίς φόρτιση"},
              {"key": "empodia", "name": "Παράνομα εμπόδια ή κώνοι από κατάστημα"},
              {"key": "p72", "name": "Αυθαίρετη ή μη εγκεκριμένη διαγράμμιση και πινακίδα P-72"}
            ]},
           {"code": "syxnotita", "variable": "true", "order": 2, "datatype": "singlevaluelist", "required": "false",
            "description": "Πόσο συχνά συμβαίνει;",
            "values": [
              {"key": "mia", "name": "Μία φορά"},
              {"key": "epanalamvanomeni", "name": "Επαναλαμβάνεται"},
              {"key": "monimi", "name": "Μόνιμα"}
            ]},
           {"code": "oxima", "variable": "true", "order": 3, "datatype": "string", "required": "false",
            "description": "Στοιχεία οχήματος, αν αφορά συγκεκριμένο όχημα (μάρκα, χρώμα, αριθμός κυκλοφορίας)"}
         ]
       }'::jsonb
FROM body b WHERE b.name = 'Αστυνομικό Τμήμα Χαϊδαρίου'
ON CONFLICT (body_id, category) DO UPDATE
  SET email = EXCLUDED.email, note = EXCLUDED.note, non_public = EXCLUDED.non_public, extra = EXCLUDED.extra,
      state = 'confirmed', editor = 'import', whenedited = now();
COMMIT;
