-- «Κατάληψη κοινόχρηστου χώρου» for every municipality: where Greece.pm (greece_route_to_dimos) sends
-- the police category's answers «Παράνομα εμπόδια ή κώνοι από κατάστημα» and «Αυθαίρετη ή μη
-- εγκεκριμένη διαγράμμιση και πινακίδα P-72», which are the municipality's to deal with. Inactive, so
-- no list offers it; private, as the police category is; its letter is the police one addressed to the
-- municipality (email_template "katalipsi"). The address is the municipality's «Άλλο»: run this again
-- after dimoi.sql or haidari.sql change an address.
BEGIN;
INSERT INTO contacts (body_id, category, email, state, editor, whenedited, note, non_public, extra)
SELECT c.body_id, 'Κατάληψη κοινόχρηστου χώρου', c.email, 'inactive', 'import', now(),
       'Εμπόδια/κώνοι καταστημάτων και αυθαίρετη διαγράμμιση/P-72 (από την κατηγορία της αστυνομίας) · ίδια διεύθυνση με το «Άλλο»',
       true, '{"email_template": "katalipsi"}'::jsonb
  FROM contacts c JOIN body b ON b.id = c.body_id AND NOT b.deleted AND b.name LIKE 'Δήμος %'
 WHERE c.category = 'Άλλο' AND c.state = 'confirmed'
ON CONFLICT (body_id, category) DO UPDATE
  SET email = EXCLUDED.email, note = EXCLUDED.note, state = 'inactive', non_public = true,
      extra = coalesce(contacts.extra, '{}'::jsonb) || EXCLUDED.extra, editor = 'import', whenedited = now();
SELECT count(*) AS municipalities FROM contacts WHERE category = 'Κατάληψη κοινόχρηστου χώρου' AND state = 'inactive';
COMMIT;
