-- Greek names of the report states, which FixMyStreet keeps in the state table (in English) and
-- shows from the translation table: without these, a body's update read «Η κατάσταση άλλαξε σε:
-- In progress». «Open» and «Closed» come from the .po.
BEGIN;
INSERT INTO translation (tbl, object_id, col, lang, msgstr)
SELECT 'state', s.id, 'name', 'el', t.msgstr
  FROM state s JOIN (VALUES
    ('investigating', 'Υπό διερεύνηση'),
    ('in progress', 'Σε εξέλιξη'),
    ('planned', 'Προγραμματίστηκε'),
    ('action scheduled', 'Προγραμματίστηκε εργασία'),
    ('unable to fix', 'Καμία περαιτέρω ενέργεια'),
    ('not responsible', 'Αναρμόδιος φορέας'),
    ('duplicate', 'Διπλή αναφορά'),
    ('internal referral', 'Παραπέμφθηκε εσωτερικά'),
    ('cancelled', 'Ακυρώθηκε'),
    ('fixed', 'Διορθώθηκε')
  ) AS t(label, msgstr) ON t.label = s.label
ON CONFLICT (tbl, object_id, col, lang) DO UPDATE SET msgstr = EXCLUDED.msgstr;
SELECT count(*) AS el_states FROM translation WHERE tbl = 'state' AND lang = 'el';
DELETE FROM translation WHERE tbl = 'state' AND lang = 'el-gr';
COMMIT;
