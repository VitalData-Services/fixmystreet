-- «Διορθώθηκε – αναμένει επιβεβαίωση»: a citizen with an email said the problem is fixed; the report
-- stays open (type open) until a moderator or the body's staff sets «Διορθώθηκε» (Greece.pm
-- process_open311_extras). Idempotent.
BEGIN;
INSERT INTO state (label, type, name)
SELECT 'fix pending', 'open', 'Fixed, awaiting confirmation'
 WHERE NOT EXISTS (SELECT 1 FROM state WHERE label = 'fix pending');
INSERT INTO translation (tbl, object_id, col, lang, msgstr)
SELECT 'state', id, 'name', 'el', 'Διορθώθηκε – αναμένει επιβεβαίωση' FROM state s
 WHERE label = 'fix pending'
   AND NOT EXISTS (SELECT 1 FROM translation t WHERE t.tbl = 'state' AND t.object_id = s.id AND t.col = 'name' AND t.lang = 'el');
COMMIT;
