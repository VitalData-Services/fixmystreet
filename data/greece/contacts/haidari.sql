-- Δήμος Χαϊδαρίου: report categories.
-- Until categories are routed separately, every category goes to the municipality's general
-- address (protokollo@, listed by the municipality, ΚΕΔΕ 2024-2028 and ΥΠΕΣ 14/08/2026). The
-- service that handles each category is kept in the note and in departments.csv.
-- Source: https://www.haidari.gr/tilefona-epikoinonias/ (read 2026-10-24).
-- Categories missing from the list below are marked deleted. Disabled/EV-charging bays go to the
-- police instead (police.sql).
BEGIN;
CREATE TEMP TABLE haidari_categories (category text, note text) ON COMMIT DROP;
INSERT INTO haidari_categories VALUES
  ('Λακκούβα ή φθορά οδοστρώματος', 'Διεύθυνση Τεχνικών Υπηρεσιών (γραμματεία), texniki@haidari.gr, 213 20 47 202'),
  ('Πρόβλημα με πεζοδρόμιο', 'Φθορές, ράμπες ΑμεΑ: Διεύθυνση Τεχνικών Υπηρεσιών, texniki@haidari.gr, 213 20 47 202 · Εμπόδια, τραπεζοκαθίσματα: Τμήμα Ελέγχου Κοινοχρήστων Χώρων, mpenekos@haidari.gr, 213 20 47 368'),
  ('Οδοφωτισμός', 'Τμήμα Ηλεκτρομηχανολογικών Έργων και Οδοφωτισμού, fkampolis@haidari.gr, 213 20 47 292'),
  ('Θέματα καθαριότητας', 'Διεύθυνση Καθαριότητας και Βιώσιμης Διαχείρισης Απορριμμάτων, pettas@haidari.gr, 210 58 18 860'),
  ('Πράσινο και δέντρα', 'Διεύθυνση Ανάπτυξης – Συντήρησης Πρασίνου, parasxou@haidari.gr, 210 58 22 368'),
  ('Άλλο', 'Αυτοτελές Τμήμα Ανταπόκρισης σε Αναφορές και Προτάσεις Πολιτών, grafiodimotihaidari@gmail.com, 213 20 47 207');

UPDATE contacts SET state = 'deleted', editor = 'import', whenedited = now()
 WHERE body_id = (SELECT id FROM body WHERE name = 'Δήμος Χαϊδαρίου')
   AND state <> 'deleted'
   AND category NOT IN (SELECT category FROM haidari_categories)
   AND category <> 'Κατάληψη κοινόχρηστου χώρου';   -- the hidden category of dimoi-katalipsi.sql

INSERT INTO contacts (body_id, category, email, state, editor, whenedited, note)
SELECT b.id, c.category, 'protokollo@haidari.gr', 'confirmed', 'import', now(), c.note
FROM body b, haidari_categories c
WHERE b.name = 'Δήμος Χαϊδαρίου'
ON CONFLICT (body_id, category) DO UPDATE
  SET email = EXCLUDED.email, note = EXCLUDED.note, state = 'confirmed', editor = 'import', whenedited = now();
COMMIT;
