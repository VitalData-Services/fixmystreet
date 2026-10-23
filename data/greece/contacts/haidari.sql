-- Δήμος Χαϊδαρίου: report categories and the service that receives each one.
-- Source: https://www.haidari.gr/tilefona-epikoinonias/ (read 2026-10-24).
BEGIN;
INSERT INTO contacts (body_id, category, email, state, editor, whenedited, note)
SELECT b.id, c.category, c.email, 'confirmed', 'import', now(), c.note
FROM body b, (VALUES
  ('Λακκούβα ή φθορά οδοστρώματος', 'texniki@haidari.gr', 'Διεύθυνση Τεχνικών Υπηρεσιών (γραμματεία), 213 20 47 202'),
  ('Φθαρμένο πεζοδρόμιο ή ράμπα ΑμεΑ', 'texniki@haidari.gr', 'Διεύθυνση Τεχνικών Υπηρεσιών (γραμματεία), 213 20 47 202'),
  ('Εμπόδιο σε πεζοδρόμιο (τραπεζοκαθίσματα, αντικείμενα)', 'mpenekos@haidari.gr', 'Τμήμα Ελέγχου Κοινοχρήστων Χώρων, 213 20 47 368'),
  ('Οδοφωτισμός', 'fkampolis@haidari.gr', 'Τμήμα Ηλεκτρομηχανολογικών Έργων και Οδοφωτισμού, 213 20 47 292'),
  ('Σκουπίδια και καθαριότητα', 'pettas@haidari.gr', 'Διεύθυνση Καθαριότητας και Βιώσιμης Διαχείρισης Απορριμμάτων, 210 58 18 860'),
  ('Πράσινο και δέντρα', 'parasxou@haidari.gr', 'Διεύθυνση Ανάπτυξης – Συντήρησης Πρασίνου, 210 58 22 368'),
  ('Άλλα', 'grafiodimotihaidari@gmail.com', 'Αυτοτελές Τμήμα Ανταπόκρισης σε Αναφορές και Προτάσεις Πολιτών, 213 20 47 207')
) AS c(category, email, note)
WHERE b.name = 'Δήμος Χαϊδαρίου'
ON CONFLICT (body_id, category) DO UPDATE
  SET email = EXCLUDED.email, note = EXCLUDED.note, state = 'confirmed', whenedited = now();
COMMIT;
