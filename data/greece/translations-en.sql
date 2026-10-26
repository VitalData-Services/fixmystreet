-- English names of the report categories (contacts.category), shown when the site is in English
-- (the menu's language switch). FixMyStreet looks them up per contact row in the translation table,
-- so every contact with the category gets one; re-running replaces them.
BEGIN;
CREATE TEMP TABLE greece_category_en (category text PRIMARY KEY, en text NOT NULL) ON COMMIT DROP;
INSERT INTO greece_category_en VALUES
  ('Λακκούβα ή φθορά οδοστρώματος', 'Pothole or damaged road'),
  ('Οδοφωτισμός', 'Street lighting'),
  ('Πράσινο και δέντρα', 'Trees and green spaces'),
  ('Πρόβλημα με πεζοδρόμιο', 'Pavement problem'),
  ('Φρεάτια και καθαριότητα', 'Drains and cleaning'),
  ('Φθαρμένο πεζοδρόμιο ή ράμπα ΑμεΑ', 'Damaged pavement or wheelchair ramp'),
  ('Εμπόδιο σε πεζοδρόμιο (τραπεζοκαθίσματα, αντικείμενα)', 'Obstruction on the pavement (tables, objects)'),
  ('Στάθμευση σε ράμπα ή θέση ΑμεΑ, πεζοδρόμιο ή διάβαση', 'Parking on a disabled ramp or bay, pavement or crossing'),
  ('Στάθμευση σε φορτιστή EV ή εμπόδιο στη διέλευση', 'Parking at an EV charger or blocking the way'),
  ('Άλλο', 'Other');
DELETE FROM translation t USING contacts c, greece_category_en g
 WHERE t.tbl = 'contact' AND t.col = 'category' AND t.lang = 'en-gb' AND t.object_id = c.id AND c.category = g.category;
INSERT INTO translation (tbl, object_id, col, lang, msgstr)
SELECT 'contact', c.id, 'category', 'en-gb', g.en
  FROM contacts c JOIN greece_category_en g ON g.category = c.category;
COMMIT;
