-- Δήμος Πειραιώς: report categories, each to the service that handles it (the owner read them from
-- the municipality's site, 2026-10-26): roads and pavements to the roads department, the rest to the
-- Technical Services directorate until their own services are known. Other categories are left alone.
BEGIN;
CREATE TEMP TABLE pir_categories (category text, email text, note text) ON COMMIT DROP;
INSERT INTO pir_categories VALUES
  ('Λακκούβα ή φθορά οδοστρώματος', 'odopapoh@piraeus.gov.gr', 'Τμήμα Οδικού Δικτύου, Αποχέτευσης, Ανοικτών Χώρων και Παιδικών Χαρών, Θηβών 78'),
  ('Πρόβλημα με πεζοδρόμιο', 'odopapoh@piraeus.gov.gr', 'Τμήμα Οδικού Δικτύου, Αποχέτευσης, Ανοικτών Χώρων και Παιδικών Χαρών, Θηβών 78'),
  ('Οδοφωτισμός', 'gramarchitec@piraeus.gov.gr', 'Διεύθυνση Τεχνικών Υπηρεσιών, Θηβών 78 · τηλ. 213 2123010'),
  ('Φρεάτια και καθαριότητα', 'kathariotita@piraeus.gov.gr', 'Καθαριότητα (owner, 2026-10-26)'),
  ('Πράσινο και δέντρα', 'gramarchitec@piraeus.gov.gr', 'Διεύθυνση Τεχνικών Υπηρεσιών, Θηβών 78 · τηλ. 213 2123010'),
  ('Άλλο', 'gramarchitec@piraeus.gov.gr', 'Διεύθυνση Τεχνικών Υπηρεσιών, Θηβών 78 · τηλ. 213 2123010');
INSERT INTO contacts (body_id, category, email, state, editor, whenedited, note)
SELECT b.id, c.category, c.email, 'confirmed', 'import', now(), c.note
  FROM body b, pir_categories c
 WHERE b.name = 'Δήμος Πειραιώς' AND NOT b.deleted
ON CONFLICT (body_id, category) DO UPDATE
  SET email = EXCLUDED.email, note = EXCLUDED.note, state = 'confirmed', editor = 'import', whenedited = now();
SELECT c.category, c.email FROM contacts c JOIN body b ON b.id = c.body_id WHERE b.name = 'Δήμος Πειραιώς' AND c.state = 'confirmed' ORDER BY 1;
COMMIT;
