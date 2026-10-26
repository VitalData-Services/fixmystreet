-- Δήμος Ραφήνας - Πικερμίου: report categories, each to the service that handles it (owner and the
-- municipality's page https://rafina-pikermi.gr/tilefona-dimoy-rafinas-pikermioy/, 2026-10-26).
-- Other categories of the municipality are left alone.
BEGIN;
CREATE TEMP TABLE raf_categories (category text, email text, note text) ON COMMIT DROP;
INSERT INTO raf_categories VALUES
  ('Λακκούβα ή φθορά οδοστρώματος', 'dty@4059.syzefxis.gov.gr', 'Τεχνική Υπηρεσία'),
  ('Πρόβλημα με πεζοδρόμιο', 'dty@4059.syzefxis.gov.gr', 'Τεχνική Υπηρεσία'),
  ('Οδοφωτισμός', 'dty@4059.syzefxis.gov.gr', 'Τεχνική Υπηρεσία'),
  ('Φρεάτια και καθαριότητα', 'kathariotita@0164.syzefxis.gov.gr', 'Καθαριότητα'),
  ('Πράσινο και δέντρα', 'prasino@0164.syzefxis.gov.gr', 'Πράσινο'),
  ('Άλλο', 'protokolo@0164.syzefxis.gov.gr', 'Πρωτόκολλο · τηλ. 22943 21001');
INSERT INTO contacts (body_id, category, email, state, editor, whenedited, note)
SELECT b.id, c.category, c.email, 'confirmed', 'import', now(), c.note
  FROM body b, raf_categories c
 WHERE b.name = 'Δήμος Ραφήνας - Πικερμίου' AND NOT b.deleted
ON CONFLICT (body_id, category) DO UPDATE
  SET email = EXCLUDED.email, note = EXCLUDED.note, state = 'confirmed', editor = 'import', whenedited = now();
SELECT c.category, c.email FROM contacts c JOIN body b ON b.id = c.body_id WHERE b.name = 'Δήμος Ραφήνας - Πικερμίου' AND c.state = 'confirmed' ORDER BY 1;
COMMIT;
