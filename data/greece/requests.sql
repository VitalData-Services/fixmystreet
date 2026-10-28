-- The request desk (Greece cobrand: App::Controller::GreeceRequests, /admin/greece/requests): rights requests
-- of citizens (GDPR Art. 15-21, a recall of what was sent, a privacy flag, a content notice) and their deadlines.
-- due = received + 1 month; extended once, with a reason, to received + 3 months. An answered request is kept
-- 3 years after the answer, then deleted (bin/greece/retention). The app connects as fms.
CREATE TABLE IF NOT EXISTS greece_request (
    id serial PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('access', 'erase', 'rectify', 'object', 'recall', 'privacy', 'notice')),
    email text NOT NULL,
    received date NOT NULL,
    due date NOT NULL,
    extended_reason text,
    status text NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'waiting', 'ready', 'answered')),
    report_ref text,
    note text,
    handled_by integer,
    answered date,
    created timestamp NOT NULL DEFAULT now(),
    updated timestamp NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS greece_request_open_idx ON greece_request (due) WHERE status <> 'answered';
ALTER TABLE greece_request OWNER TO fms;
