# Plausible retention (not applicable now: the instance is run by a third party)

Instance: plausible.taneda.dev (Plausible Community Edition, ClickHouse). Site added: fixmystreets.gr.
Rule: delete statistics older than 24 months. Plausible stores no IP and no cookie, but the period is stated in our DPIA.

Run on the instance's host (check the names first with DESCRIBE; they differ a little between versions):

    docker exec -it <clickhouse-container> clickhouse-client
    SHOW TABLES FROM plausible_events_db;
    DESCRIBE plausible_events_db.events_v2;     -- time column: timestamp
    DESCRIBE plausible_events_db.sessions_v2;   -- time column: timestamp (and start)
    ALTER TABLE plausible_events_db.events_v2   MODIFY TTL timestamp + INTERVAL 24 MONTH;
    ALTER TABLE plausible_events_db.sessions_v2 MODIFY TTL timestamp + INTERVAL 24 MONTH;
    SELECT name, engine_full FROM system.tables WHERE database='plausible_events_db' AND name IN ('events_v2','sessions_v2');

The TTL applies to every site on the instance, not only fixmystreets.gr; confirm that is acceptable to the other site owners.
Verify: engine_full of both tables ends with TTL timestamp + toIntervalMonth(24).
