# fixmystreets.gr infrastructure security review (read-only)

Date: 2026-10-29 (checks ran 2026-10-28 23:45 to 2026-10-29 01:55 UTC). Scope: fms VM 10.0.201.30, build VM 192.168.10.23, relay infra9 192.168.201.81, old relay 193.123.36.218, public site.
Method: read-only commands and plain GET requests to our own site. Nothing was changed.
Two small deviations, both harmless: (a) I ran `docker run --rm --entrypoint cat <image> /etc/os-release` on the fms VM for 5 images to read the base OS (five short-lived containers created and removed); (b) I sent one POST to https://fixmystreets.gr/auth with a non-existent address and a wrong password while looking for a session cookie. It created no data but counts against the form rate budget. Also: the app container was restarted by someone else during the review (502 for about a minute); not caused by this review.

## Summary

| Severity | Count |
|---|---|
| critical | 0 |
| high | 3 (F1-F3) |
| medium | 9 (F4-F12) |
| low | 8 (F13-F20) |
| info / good | see the last two sections |

Top findings: F1 no backups found, F2 app image is Debian 11 (EOL), F3 Postgres 13.11 EOL and about three years of minor patches missing, F4 infra9 relays for 192.168.0.0/16 and 10.0.0.0/16 without authentication, F5 the app container holds the Postgres superuser password and can rewrite its own code and config.

## Things I could NOT check

- Cloudflare side: tunnel ingress, WAF, Access policies, SSL mode, bot rules, Turnstile rules. The tunnel runs with a token (`/etc/cloudflared/` holds only `token`, no config.yml), so the origin mapping lives in the Cloudflare dashboard.
- Veeam / Proxmox / hypervisor snapshots (F1).
- Session cookie flags on the live site: no cookie was set for anonymous GET of `/`, `/reports`, `/around`, `/contact`, `/alert`, `/auth`, or for one failed login POST. See F13.
- The `fms-mail` SSH key privileges on infra9 and the old relay (my last probe hung and was cancelled).
- infra9 SASL over port 25 without TLS (F9, unsure).
- Whether `bin/install_packages` (sudo NOPASSWD for `fms` inside the image) is writable by `fms`.

## High

### F1. No backup of the database or the photos was found (high, pending verification)
Evidence:
- `crontab -l` for root and debian: "no crontab for root / no crontab for debian".
- `/etc/cron.d/` holds only fixmystreets-{all-reports,anonymise-old,departments-review,digest,mail-delivery,purge-originals,requests-reminder,retention,video-sweep} plus e2scrub. None runs pg_dump.
- `find / -name "*.sql" -o -name "*.sql.gz" -o -name "*.dump" -o -name "*backup*"` found only repo seed SQL files.
- Data lives in docker volumes `fixmystreet_fixmystreet-pgdata`, `fixmystreet_fixmystreet-originals`, `fixmystreet_fixmystreet-videos` and bind `/data/fms/uploads`, all on one 59 GB disk (`/dev/sda1`).
Risk: one disk failure, bad migration, ransomware or operator error loses every report, user and photo. A VM-level backup (Veeam/Proxmox) may exist; I could not see it. A VM image is also not a consistent database backup.
Fix: nightly `docker exec fixmystreet-postgres-1 pg_dump -U postgres -Fc fixmystreet`, encrypted (age/gpg), copied to a different host, 14 to 30 days retention; same for uploads/originals/videos; restore test each quarter; confirm the VM is in Veeam/Proxmox backup and write it down. Backups must expire in line with the privacy page retention (24 months anonymisation).

### F2. The app image is Debian 11 (bullseye), end of life (high)
Evidence: `docker run --rm --entrypoint cat fixmystreets-gr /etc/os-release` gives `Debian GNU/Linux 11 (bullseye)`; Dockerfile `FROM jgoerzen/debian-base-standard:bullseye`. Debian 11 LTS ended 2026-08-31, so no more security updates for Perl, OpenSSL, image libraries or the systemd inside the image. This container parses citizen uploads on a public site.
Risk: new CVEs in image/TLS/Perl libraries stay unpatched; photo handling is the most likely entry route.
Fix: rebuild on bookworm or trixie; meanwhile `apt-get upgrade` at every build and rebuild weekly. Other images are fine: postgres Debian 12, video Debian 12, anonymiser and mapit-local Debian 13.

### F3. PostgreSQL 13.11 is end of life and far behind its minor releases (high, medium if you weigh the LAN-only exposure)
Evidence: `select version()` -> `PostgreSQL 13.11 (Debian 13.11-1.pgdg120+1)`. PG 13 upstream support ended November 2025; 13.11 dates from 2023, so every later security fix is missing.
Risk: known server CVEs unpatched. Exposure is limited: port 5432 is not published to the host, the app role `fms` is not a superuser.
Fix: move to PG 16/17 (dump and restore into a new volume, rehearse on preprod), at least bump to the latest 13.x now.

## Medium

### F4. infra9 accepts relay from 192.168.0.0/16 and 10.0.0.0/16 without authentication (medium)
Evidence (`ssh infra9 postconf -n`): `mynetworks = 127.0.0.0/8 192.168.0.0/16 10.0.0.0/16`; `smtpd_relay_restrictions = permit_mynetworks permit_sasl_authenticated defer_unauth_destination`. fms (10.0.201.30) sends to `relayhost = [192.168.201.81]:25` with no SASL, so it depends on this range.
Risk: any host or compromised device in those two /16 ranges can send mail from infra9 as anything@fixmystreets.gr. infra9's egress 62.4.15.126 is in the SPF record, so SPF passes; with `aspf=s` an attacker only needs an envelope sender in fixmystreets.gr, so DMARC `p=reject` does not stop it. That allows convincing phishing in the site's name to citizens and municipalities.
Fix: shrink `mynetworks` to the hosts that really need it (`10.0.201.30/32` for fms). infra9 already has a SASL listener `192.168.201.81:2587` (TLS required, `smtpd_sender_login_maps`, rate limit 60); move fms there with an account limited to fixmystreets.gr senders. Also review the `smtp ... -o smtpd_sasl_auth_enable=yes`, `smtps` and `submission` entries in master.cf.

### F5. The app container holds the Postgres superuser password and can rewrite its own code and config (medium)
Evidence:
- Container env of `fixmystreet-fixmystreet-1` contains FMS_DB_PASS, SUPERUSER_PASSWORD and POSTGRES_PASSWORD (names only; values never printed). compose line 119 sets `POSTGRES_PASSWORD` in the app service. The app only needs the `fms` role.
- Mounts that are rw=true (docker inspect): `conf/general.yml-local` (mode 640, owner debian = uid 1000 = the container's `fms` user, so the app can overwrite its own config), the directory `templates/web/greece`, and controllers `GreeceApprove.pm`, `GreeceHandbook.pm`, `GreeceReportRef.pm`, `GreeceRequests.pm`. Starman runs as `fms` (uid 1000), which maps to host user debian (sudo NOPASSWD, docker group).
- `/sys/fs/cgroup` is bind-mounted rw (the base image runs full systemd), `cgroupns=host`. The container is not `privileged`, has no added capabilities and no docker.sock.
Risk: a code-execution bug in the app (photo parsing, template injection) lets an attacker persist by editing controllers/templates on the host, read all secrets and log in to Postgres as superuser.
Fix: remove POSTGRES_PASSWORD (and SUPERUSER_PASSWORD after the first start) from the app service; mount all of the above `:ro`; make general.yml-local `root:1000 0440`; drop the cgroup bind mount or use `cgroupns: private`; add `cap_drop: [ALL]` and `security_opt: [no-new-privileges:true]`.

### F6. Content-Security-Policy is report-only and allows unsafe-inline and unsafe-eval (medium)
Evidence (`curl -sI https://fixmystreets.gr/`): `content-security-policy-report-only: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://challenges.cloudflare.com https://plausible.taneda.dev; ...`. No enforcing CSP and no `report-uri`/`report-to`.
Risk: a stored XSS (report text is shown to other people) is not blocked, and nobody receives violation reports.
Fix: add `report-to`, collect for a week, move to nonces/hashes, then enforce. Drop `plausible.taneda.dev` if Plausible really was removed.

### F7. Logging: very short retention, no central log, no alerting or intrusion detection (medium)
Evidence:
- nginx log driver json-file `max-size 10m, max-file 3`; `docker logs fixmystreet-nginx-1` held 17,998 lines, all dated 28/Oct/2026 (about a day), mostly ClaudeBot on `/around`.
- No fail2ban, auditd, crowdsec or wazuh: `systemctl is-active auditd crowdsec wazuh-agent ufw nftables` -> all inactive; `fail2ban-client: command not found`.
- The app's own access log inside the container shows the Docker gateway `172.18.0.1` as client, not the visitor. nginx logs the visitor only in the last field (X-Forwarded-For).
- Cron output goes to `/var/log/fixmystreets/*.log`, rotated weekly, 8 kept.
Risk: an intrusion, brute force or scrape would go unnoticed and could not be reconstructed after a day.
Fix: ship nginx, app, auth.log and docker events to the central log host, keep 30 to 90 days with IP truncation after that; alert on 5xx spikes, many 429s, failed /admin and /auth logins, new SSH logins; make the app see the real client IP (nginx `real_ip` from the docker bridge, or trust X-Forwarded-For in the app).

### F8. Docker resource limits: only 3 of 8 containers have any (medium/low)
Evidence (`docker inspect`): mem limits only on video (768 MB), anonymiser (1536 MB), mapit-local (256 MB). app, nginx, postgres, memcached, tiles: `mem=0 cpu=0`, `pids=<no value>`. Host RAM 7.9 GB, 41 GB disk free.
Risk: a flood or a runaway job starves Postgres or the host and takes the site down.
Fix: add `mem_limit`, `cpus`, `pids_limit` to app, postgres, tiles, nginx; `read_only: true` with tmpfs for nginx, memcached, tiles.

### F9. Mail transport hygiene: opportunistic TLS, snakeoil certificate, old relay without TLS (medium, partly unsure)
Evidence:
- fms postfix (`postconf -n`): `smtp_tls_security_level = may`, `smtpd_tls_cert_file = /etc/ssl/certs/ssl-cert-snakeoil.pem`, `milter_default_action = accept`, `mynetworks = 127.0.0.0/8 172.16.0.0/12`, `smtpd_relay_restrictions = permit_mynetworks, reject`, `inet_interfaces = all`. Queue empty. Not an open relay: anything outside the Docker range is rejected.
- infra9: `smtpd_tls_security_level = may`; outbound `smtp_tls_security_level = dane` (good). port 25 has `-o smtpd_sasl_auth_enable=yes` and I saw no global `smtpd_tls_auth_only`, so SASL could be offered in clear text (unsure, not tested).
- Old relay rocky@193.123.36.218: `smtpd_tls_security_level = none`, `mynetworks = 127.0.0.0/8 192.168.201.81/32 192.168.203.0/24 62.210.29.55/32`, `smtpd_relay_restrictions = permit_mynetworks, reject_unauth_destination`. Not an open relay, but plaintext only.
- `milter_default_action = accept` on fms: if opendkim stops, mail goes out unsigned, and with DMARC `p=reject` receivers then drop it silently.
Risk: report content (names, phones, addresses) can travel unencrypted if any hop falls back; if the old relay is still in any path for fixmystreets.gr, that leg crosses the internet in clear text (memory says OCI was removed from routing; I could not confirm).
Fix: `smtp_tls_security_level = encrypt` on fms -> infra9 (client cert `/etc/postfix/tls/fms-client.crt` already exists); `smtpd_tls_auth_only = yes` on infra9; retire the old relay or give it a real certificate; `milter_default_action = tempfail` on fms; `inet_interfaces = 127.0.0.1, 172.18.0.1` (see F16).

### F10. Secrets: well kept out of git, but concentrated and visible to root and docker group (medium)
Evidence: `/opt/fixmystreet/.env` mode 600 debian; `conf/general.yml-local` 640 debian:debian; `~/.ssh/fms-mail` 600 (private key used to reach the mail hosts); `/etc/opendkim/keys/fixmystreets.gr` 700 opendkim. Kinds of secret in general.yml-local (names only): DB password, SMTP_PASSWORD, Google/Facebook/Twitter/Twilio/Bing/Google Maps keys and social-login secrets. The same DB and superuser passwords are in the container env (F5), readable by `docker inspect`.
Good: both files are gitignored (`.gitignore:76 /.env`, `.gitignore:77 /conf/general.yml-local`, confirmed with `git check-ignore -v`); `git log --all -- conf/general.yml-local .env` is empty; the public fork clone `/tmp/pubcheck` (remote `VitalData-Services/fixmystreet`, public fork) was scanned with gitleaks: 27,076 commits, 66 hits, all upstream mySociety noise (UK tracking codes, test fixtures, `ubuntu-xenial...console.log`), none in our commits, none in `*reece*` files, `conf/general.yml-docker` or `docker-compose.yml`. `docker history --no-trunc fixmystreets-gr` showed no password/secret/token strings. Compose uses `${VAR:?}` from .env, no literal secrets.
Risk: root on the VM (debian has `NOPASSWD: ALL` and docker) exposes everything; the `fms-mail` key is a pivot to infra9 and the old relay.
Fix: delete unused keys (Facebook, Twitter, Twilio, Bing) from general.yml-local; restrict the `fms-mail` key on the mail hosts (forced command / `restrict`, read-only log access); rotate SMTP and OAuth secrets if the host or repo was ever shared; prefer docker secrets/files over env.

### F11. Build VM is a hub and is not patched automatically (medium)
Evidence on 192.168.10.23: `apt list --upgradable` shows 22 security-origin lines (chromium 154 -> 156, ca-certificates, containerd.io, docker-ce-cli ...); `systemctl is-enabled unattended-upgrades` -> "Failed to get unit file state ... No such file or directory" (not installed); kernel `6.1.0-53-amd64`, up 17 days, 7 users logged in; `/` is 85% used (27 GB free); NTP synchronised. It holds root SSH access to fms, infra9 and the old relay.
Risk: a compromise of the build VM gives root on all of those hosts.
Fix: install and enable unattended-upgrades, apply updates and reboot to the newer kernel, free disk, use per-target keys with `from=` restrictions.

### F12. /admin is reachable from the internet; no Cloudflare-level gate verified (medium)
Evidence: `curl https://fixmystreets.gr/admin` -> 302 (to login). `/tiles/` returns the TileServer GL index page (200). Two superuser accounts exist (`select count(*) from users where is_superuser` -> 2). The app has a two-factor controller (GreeceTwoFactor.pm); enforcement not verified.
Risk: the admin interface can be brute forced or attacked through any FixMyStreet admin bug from anywhere; only the shared `form_posts` rate limit applies.
Fix: Cloudflare Access (Google, named accounts) in front of `/admin*` and `/greece/approve*`, or an IP allow rule; enforce 2FA for all superusers; expose only style/tile paths of tileserver, not its index and data listing.

## Low

### F13. Cookie flags could not be verified live (low, unsure)
Evidence: `curl -D -` for `/`, `/reports`, `/around`, `/contact`, `/alert`, `/auth` and one failed POST to `/auth` returned no `Set-Cookie` (anonymous visitors get no cookie, which is good). Code: `perllib/FixMyStreet/App.pm:72 cookie_secure => 2` (Secure when https); Catalyst default HttpOnly; no explicit SameSite (browser default Lax). `GreeceSocial.pm` sets `HttpOnly; Secure; SameSite=None` on its short CSRF cookie on purpose (Apple callback is cross-site).
Fix: after a real login on staging check `Set-Cookie` shows `Secure; HttpOnly; SameSite=Lax`; set SameSite explicitly.

### F14. HSTS without includeSubDomains/preload; no CAA, DNSSEC, MTA-STS or TLS-RPT (low)
Evidence: `strict-transport-security: max-age=31536000`; `dig CAA fixmystreets.gr`, `dig DS fixmystreets.gr`, `dig TXT _mta-sts.fixmystreets.gr`, `_smtp._tls` all empty. Present and good: `x-frame-options: SAMEORIGIN`, `x-content-type-options: nosniff`, `referrer-policy: strict-origin-when-cross-origin`, `permissions-policy: camera=(self), microphone=(self), geolocation=(self), payment=(), usb=(), serial=()`.
Fix: add includeSubDomains when all subdomains are https; CAA records; DNSSEC in Cloudflare; MTA-STS (mode testing first) and TLS-RPT.

### F15. SSH on fms: root login with key, X11 forwarding, no fail2ban, no host firewall (low)
Evidence: `sshd -T`: `permitrootlogin without-password`, `passwordauthentication no`, `pubkeyauthentication yes`, `maxauthtries 6`, `x11forwarding yes`, listening on 0.0.0.0:22 and [::]:22. `systemctl is-active fail2ban` -> inactive (not installed). `iptables -S`: `-P INPUT ACCEPT`, only Docker chains. 0 failed or invalid SSH attempts in the last 24 h (`journalctl -u ssh`). 2 keys in `debian` authorized_keys, 2 in root's. `sudo -l -U debian`: `(ALL) NOPASSWD: ALL`; debian is in the `docker` group.
Risk: low today (key-only, reachable only inside the LAN as far as I can tell), but one stolen key means full control, and there is no second layer if exposure changes.
Fix: `PermitRootLogin no`, `X11Forwarding no`, `AllowUsers debian`, `MaxAuthTries 3`; nftables input policy drop with 22 allowed from the admin subnet; remove unneeded keys.

### F16. Network exposure summary (low/info)
Evidence (`ss -ltnp`, `docker ps`):
- Docker publishes only `127.0.0.1:8000` and `[::1]:8000` (nginx). The other containers expose ports only inside `fixmystreet_default` (`9000`, `5432`, `11211`, `8080`).
- Host listeners: `0.0.0.0:22` sshd, `0.0.0.0:25` postfix, `0.0.0.0:5355` and `[::]:5355` LLMNR (systemd-resolved), `127.0.0.53:53`, `127.0.0.54:53`, `127.0.0.1:8891` opendkim, `127.0.0.1:20241` cloudflared metrics.
- Internet path: Cloudflare -> cloudflared (token mode, outbound only) -> `127.0.0.1:8000` -> nginx.
Reachable from the LAN only: SSH, SMTP (relay denied), LLMNR. Nothing else is reachable from outside as far as I can see.
Fix: postfix `inet_interfaces = 127.0.0.1, 172.18.0.1`; `LLMNR=no` in resolved.conf; host firewall of F15.

### F17. nginx: limits are good, a few gaps (low)
Evidence from `conf/nginx.conf-docker`; the live container file is identical (`diff` printed `live==repo`):
- Zones: `places_rate` 5r/s, `video_start` 6r/m, `otp_send` 3r/m, `mapit_rate` 5r/s, `form_posts` 2r/m burst 5 (report, import, update, auth, alerts, contact, privacy), `votes` 20r/m. They key on `$http_cf_connecting_ip` (spoofable only by someone who can reach 127.0.0.1:8000, which needs a local foothold; non-CF requests count by their own address).
- `client_max_body_size 10m` (also for video chunks). No `client_header_timeout`, `client_body_timeout`, `limit_conn`; `server_tokens` not turned off (Cloudflare hides it).
- Paths tested on https://fixmystreets.gr: `/admin` 302, `/mapit/` 404, `/mapit/area/N.geojson` allowed and cached, `/tiles/` 200, `/greece/` 404, `/upload/` 404, `/server-status` 404, `/nginx_status` 404, `/.git/config` 404, `/.env` 404, `/conf/general.yml` 404, `/rss` 410, `/robots.txt` 200. Photos only go through the app controller.
- Static locations and `/tiles/` repeat only HSTS and nosniff (nginx add_header inheritance, as the config comment says): acceptable.
- No `real_ip` config: the app sees `172.18.0.1` (F7).
- TLS: nginx listens only on loopback port 80; TLS is terminated by Cloudflare and the cloudflared tunnel. I could not check the Cloudflare minimum TLS version.
Fix: `server_tokens off; client_header_timeout 10s; client_body_timeout 20s;`; restrict `/tiles/` to tile/style paths; add a Cloudflare rate rule for `/around` and `/report/new`.

### F18. PostgreSQL configuration (low)
Evidence (`psql -U postgres` inside `fixmystreet-postgres-1`): `listen_addresses=*` (in the container), `ssl=off`, `password_encryption=md5`, `log_connections=off`, `max_connections=100`. `pg_hba.conf` active lines: `local all all trust`, `host all all 127.0.0.1/32 trust`, `host all all ::1/128 trust`, `local/host replication ... trust`, `host all all all md5`. Roles: `fms` (not superuser, no createrole, has CREATE on the database), `postgres` superuser. Passwords are 48 characters (postgres) and 24 (app superuser password) and not in the short default list I tested (values never printed). One application database `fixmystreet`, 7 users at the time.
Risk: low, because 5432 is not published and the Docker network is private. `trust` on loopback is container-local. md5 is weak; no TLS between app and DB (single host, acceptable).
Fix: `password_encryption=scram-sha-256` and re-set role passwords; `log_connections=on`; revoke CREATE on schema public from `fms` after migrations; these come with the PG upgrade (F3).

### F19. Cron jobs and scripts (low/info)
Evidence: 9 jobs in `/etc/cron.d/fixmystreets-*`, files `root:root 644`, all run as `debian`, scripts in `/opt/fixmystreet/bin/greece/` owned by debian. No lower-privileged account can write them; the container user maps to uid 1000 = debian, so a compromised app that writes the rw-mounted paths of F5 reaches debian-owned files, and debian already has NOPASSWD sudo (no separate privilege boundary). Logs `/var/log/fixmystreets/*.log` are `-rw-r--r-- debian`; `digest.log` contains municipality addresses and counts, not citizen data (I read only a few lines; not a full audit). logrotate `/etc/logrotate.d/fixmystreet*`: weekly, rotate 8, compress, missingok, notifempty. purge-originals runs every 15 minutes and logs nothing (nothing to purge).
Fix: `chmod 640` on the logs; keep citizen data out of cron logs; consider a root-owned copy of scripts for cron.

### F20. fms-mail SSH key (low, unverified)
Evidence: cron.d comment: "the relay and the mailbox host are reached with ~/.ssh/fms-mail of user debian"; key mode 600. I could not see what it can do on infra9 and the old relay.
Fix: limit it on the target side to a read-only log reader (`command=`, `restrict`).

## Info / positive findings

- OS patch state, fms VM: Debian 12, kernel `6.1.0-54-amd64`, up 5 days, unattended-upgrades installed and enabled (`APT::Periodic::Unattended-Upgrade "1"`), pending only bind9-host/bind9-libs (oldstable-security) and cloudflared 2026.10.4 -> 2026.10.5; no reboot required; `System clock synchronized: yes`; time zone UTC; disk 17 G used of 59 G (29%); Docker 29.9.2.
- Containers: no `privileged`, no `docker.sock` mount (`grep docker.sock docker-compose.yml` empty), no extra capabilities. Users: app image starts as root (systemd) but starman runs as `fms`; tiles `node`, video `fmsvideo`, memcached `memcache`, mapit-local `nobody`; nginx and postgres use the image default. Restart policies `unless-stopped` or `always`. Images: `nginx:1.27.2` (old, update), `memcached:1.6.32`, `tileserver-gl:v5.6.0`; app, video, anonymiser, mapit-local are local `:latest` builds (not pinned).
- Dockerfile (upstream) gives `fms` NOPASSWD sudo for `bin/install_packages`; not checked whether it is writable by fms.
- Site is in staging mode (`STAGING_SITE: 1`); before go-live confirm it is off and no staging-only behaviour remains.
- Email authentication of fixmystreets.gr is strong: SPF `v=spf1 ip4:193.123.36.218 ip4:62.210.29.55 ip4:62.4.15.126 mx ~all` (62.4.15.126 = infra9 egress, 193.123.36.218 = old relay, 62.210.29.55 = MX); DKIM selector `fms2026` published, RSA (2048-bit length), signed by opendkim (relaxed/simple, `Mode sv`); DMARC `v=DMARC1; p=reject; rua=mailto:dmarc-reports@fixmystreets.gr; ruf=mailto:dmarc-forensics@fixmystreets.gr; pct=100; adkim=s; aspf=s`. Suggestions: drop the old relay IP from SPF when it is retired; the `ruf` mailbox receives message copies, treat it as personal data; MTA-STS absent (F14).
- The MX `mail.fixmystreets.gr` resolves to 62.210.29.55 (not behind Cloudflare); I did not probe it.
- Data hygiene jobs are running (24-month anonymisation, token purge, original photo purge every 15 minutes, video sweep hourly). nginx logs are kept about a day, which is good for privacy and bad for forensics (F7).

## Item 10: other risks for a site holding names, phone numbers, emails and photos

1. Photos: EXIF/GPS and number plates. A purge job deletes the police originals; I did not test that public copies are re-encoded without EXIF.
2. `/data/fms/uploads` is mode 755 with 644 files owned by debian; restrict to 750/640.
3. The public GitHub fork exposes your nginx config, cron.d files and operational comments (host names `freevium1`, `infra9`, `~/.ssh/fms-mail`). No secrets, but it is a map for an attacker. Consider keeping `conf/greece/cron.d` and operational notes in a private repo.
4. Turnstile is in the CSP; confirm it is enforced server-side on report creation, OTP send and sign-in, since reporting needs no account and the only other control is the per-IP nginx rate limit.
5. Mail-bomb through the "email me a code / confirmation" paths is limited per visitor IP only; a botnet bypasses it. Add per-recipient and per-day caps in the app.
6. One VM with one disk holds the database, photos, config and the tunnel (see F1).
7. GDPR: when central logging is added (F7) define retention and legal basis for IP addresses.
