-- The priorities a staff member can give a report (the «Προτεραιότητα» list of the report page and of the admin
-- edit page): two, for every body (owner, 2026-10-29). Run again after bodies are added: it adds only what is missing.
INSERT INTO response_priorities (body_id, name, description, is_default)
SELECT b.id, p.name, p.description, p.name = 'Κανονική'
  FROM body b
 CROSS JOIN (VALUES ('Υψηλή - κίνδυνος ατυχήματος', 'Κίνδυνος ατυχήματος: να αντιμετωπιστεί πρώτο'),
                    ('Κανονική', 'Κανονική προτεραιότητα')) AS p(name, description)
 WHERE b.deleted = false
ON CONFLICT (body_id, name) DO NOTHING;
-- «Κανονική» is the default priority (owner, 2026-10-31).
UPDATE response_priorities SET is_default = true WHERE name = 'Κανονική' AND NOT deleted;
