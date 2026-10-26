-- Δήμος Παλαιού Φαλήρου: report categories, each to the service that handles it (the owner read them
-- from the municipality's contact page, 2026-10-26). Other categories of the municipality are left alone.
BEGIN;
CREATE TEMP TABLE pf_categories (category text, email text, note text) ON COMMIT DROP;
INSERT INTO pf_categories VALUES
  ('Λακκούβα ή φθορά οδοστρώματος', 'ty.dpf@palaiofaliro.gr', 'Δ/νση Τεχνικών Υπηρεσιών, Τερψιχόρης 51 και Αρτέμιδος · τηλ. 213 2020315'),
  ('Πρόβλημα με πεζοδρόμιο', 'ty.dpf@palaiofaliro.gr', 'Δ/νση Τεχνικών Υπηρεσιών, Τερψιχόρης 51 και Αρτέμιδος · τηλ. 213 2020315'),
  ('Οδοφωτισμός', 'ty.dpf@palaiofaliro.gr', 'Δ/νση Τεχνικών Υπηρεσιών, Τερψιχόρης 51 και Αρτέμιδος · τηλ. 213 2020315'),
  ('Φρεάτια και καθαριότητα', 'amaxi.dpf@palaiofaliro.gr', 'Τμ. Καθαριότητας, Αγ. Πέτρου & Σωκράτους 5 · τηλ. 210 9844057 ή 1565'),
  ('Πράσινο και δέντρα', 'd.perivallon@palaiofaliro.gr', 'Δ/νση Περιβάλλοντος - Πρασίνου, Τερψιχόρης 51 και Αρτέμιδος · τηλ. 213 2020326'),
  ('Άλλο', 'ty.dpf@palaiofaliro.gr', 'Δ/νση Τεχνικών Υπηρεσιών, Τερψιχόρης 51 και Αρτέμιδος · τηλ. 213 2020315');
INSERT INTO contacts (body_id, category, email, state, editor, whenedited, note)
SELECT b.id, c.category, c.email, 'confirmed', 'import', now(), c.note
  FROM body b, pf_categories c
 WHERE b.name = 'Δήμος Παλαιού Φαλήρου' AND NOT b.deleted
ON CONFLICT (body_id, category) DO UPDATE
  SET email = EXCLUDED.email, note = EXCLUDED.note, state = 'confirmed', editor = 'import', whenedited = now();
SELECT c.category, c.email FROM contacts c JOIN body b ON b.id = c.body_id WHERE b.name = 'Δήμος Παλαιού Φαλήρου' AND c.state = 'confirmed' ORDER BY 1;
COMMIT;
