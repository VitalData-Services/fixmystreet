# fixmystreets.gr - third-party code and repository review (read-only)

Date: 2026-10-29. Reviewer: Claude (read-only; nothing changed, pushed, sent or attacked).
Tools: gitleaks 8.30.1, trivy 0.75.0 (image scans, HIGH/CRITICAL with a fix available), osv-scanner 2.6.0, osv.dev API, CPANSA (briandfoy/cpan-security-advisory, cloned 2026-10-29) matched by a script against the image's cpanfile.snapshot, a custom regex scan of every added line in the Greece-era history of both repos, GitHub advisories page and releases API for mysociety/fixmystreet.
Scratch outputs on the build VM: /tmp/privcheck.git (mirror of the private repo), /tmp/pubcheck (public fork), /tmp/trivy_*.json, /tmp/gl_pub.json, /tmp/gl_priv.json (redacted), /tmp/scan_pub.txt, /tmp/scan_priv.txt.

## 0. Key framing fact (read first)

What RUNS is NOT the code in the private repo's tree. docker/greece/Dockerfile is `FROM fixmystreet/fixmystreet:stable`, a floating tag. The local image is fixmystreet/fixmystreet:stable id cb7e35b28c89, built 2024-11-15 = upstream release v6.0, Debian 11.7 (bullseye), Perl 5.32.1. Greece Perl/templates/JS are bind-mounted over it (docker-compose.yml). So:
- Runtime core code = upstream v6.0 (2024-11-15), about 23 months old; Perl modules, OS packages and vendored JS all come from that image.
- The private repo master is a DIFFERENT base: upstream master at 8b311138c5 (git describe v6.0-1689-g8b311138c5, 2026-10-22) plus 212 Greece commits. Its cpanfile/snapshot already contain upgraded dependencies that the running image does NOT have (section 2).
- The public fork (VitalData-Services/fixmystreet, branch greece) is based on tag v6.0 (691e1b8cc8) plus 113 Greece commits, i.e. it matches the running image, not the private repo. Public history is a rewrite (14,883 commits vs 16,671 private; only author "VitalData Services <noreply@fixmystreets.gr>" for Greek commits). Private has branch backup/pre-public-20261024.
- Side risk (medium, reliability): perllib/Utils.pm and perllib/FixMyStreet/Script/UpdateAllReports.pm are mounted from the 2026 master tree into the v6.0 image. Files from a newer base can silently diverge from v6.0 callers. Verify they equal the v6.0 versions plus the Greek patch (the public fork's copy is based on v6.0).

## 1. Upstream base and security fixes since

- Newest upstream release/tag is still v6.0 (GitHub releases API: v6.0 2024-11-15, v5.0 2023-10-06, v4.0 2021-12-03). There are 1,689 upstream commits since v6.0 and no later release.
- mysociety/fixmystreet has NO published GitHub security advisories ("There aren't any published security advisories") and the CHANGELOG has no security section. So I cannot list upstream CVEs or advisories; none exist publicly. Unsure: fixes may exist as unlabelled commits; I did not audit 1,689 commits.
- Security-relevant upstream changes after v6.0 that the running image lacks:
  - Dependency upgrades (see 2): Catalyst::Plugin::Session 0.37 -> 0.44, DBIx::Class::EncodedColumn, Starman 0.4014 -> 0.4018, HTML::FormHandler, Net::DNS, Net::OAuth, URI, DBD::Pg, DBI, Email::MIME 1.954 (CVE-2024-4140), HTTP::Tiny 0.090, XML::LibXML 2.0210, Mozilla::CA, Authen::SASL, CryptX, JSON::XS/Cpanel::JSON::XS.
  - cpanm/carton hardened for HTTPS (#5437), jQuery 3.7.1, permission split report_view_private/report_mark_private, "Require view dashboard permission in order to view the dashboard", EXIF strip for photos imported via media_url (#5841).
- Applies to us: all dependency upgrades (we run the old ones). Permission/dashboard changes matter only for staff-permission hardening (low). We are missing all of them because the image was never rebuilt.
- Fix: build our own image from a pinned upstream commit with the upgraded cpanfile.snapshot, on a supported OS. `docker pull` will not help: upstream's image is stale (last built 2024-11-15).

## 2. Perl dependencies

Method: CPANSA advisories matched against the image's cpanfile.snapshot (449 dists); installed versions confirmed by loading modules inside the running container. Caveats: CPANSA feed text is sometimes truncated; I matched versions only; "applies to us" is my judgement of how FixMyStreet and our config use the module. Snapshot-only modules not installed in the container (Spreadsheet::*, Archive::Zip, Data::ICal, Imager, Image::Magick Perl module is apt) were ignored.

Installed: Catalyst::Runtime 5.90124; Template 2.29; DBD::Pg 3.8.0 (master 3.21.2); DBI 1.623 (1.656); Plack 1.0047; Starman 0.4014 (0.4018); Net::Server 2.009; LWP 6.61; IO::Socket::SSL 2.066; Net::SSLeay 1.85; HTTP::Tiny 0.076; Mozilla::CA 20211001; Email::MIME 1.946; Email::Sender 1.300035; XML::LibXML 2.0132; URI 1.71; YAML 1.28; Net::DNS 1.33; Net::OAuth 0.28; HTML::FormHandler 0.40068; Crypt::OpenSSL::RSA 0.33; CryptX 0.069; Catalyst::Plugin::Session 0.37.

- HIGH Catalyst::Plugin::Session 0.37: CVE-2025-40924, session IDs generated from a weak/predictable source (fixed 0.44). FMS uses Catalyst sessions (DBIC store) for all logins, so it applies. Practical exploitability depends on the attacker predicting pid/time/rand state, so high not critical. Fix: >=0.44 (upstream pinned it in c52f3d378d); invalidate sessions after upgrade.
- MEDIUM DBIx::Class::EncodedColumn 0.00015: CVE-2025-27551, CVE-2025-27552 (rand() used for salts). Used for bcrypt password hashing. Salts are not secret; impact is reduced salt randomness. Fix: >=0.11.
- MEDIUM HTML::FormHandler 0.40068: CVE-2022-4993 (rated critical by the feed: attacker-selected method calls), CVE-2026-19872, CVE-2026-85484/85485/85630 (label rendering XSS). FMS builds its forms with it. Preconditions need attacker-controlled form metadata or admin-entered labels; unsure of exact preconditions. Fix: >=0.410002.
- MEDIUM Starman 0.4014: CVE-2026-40560 HTTP request smuggling (fixed 0.4018). Starman sits behind nginx behind cloudflared, which normalises requests; residual risk low-medium. Fix: >=0.4018.
- MEDIUM Catalyst::Plugin::Authentication 0.10022 (CVE-2026-5091, fixed 1.0026) and Catalyst::Plugin::Static::Simple 0.36 (CVE-2026-15743, no fix listed for <=0.38): descriptions truncated in the feed; unsure of impact. Serve statics from nginx, deny dotfiles.
- MEDIUM Template Toolkit 2.29: CVE-2026-5090 (Template::Plugin::HTML escaping, fixed 3.103). Only matters if templates use that plugin rather than the `| html` filter; probably not exploitable, unsure.
- MEDIUM Email::Sender 1.300035: CVE-2026-93012 (Sendmail transport command injection, fixed 2.602). Only if the Sendmail transport is used; we relay via Postfix over SMTP (host.docker.internal), so probably not. Verify transport in conf/general.yml-local (not read).
- MEDIUM libwww-perl 6.61 / HTTP::Tiny 0.076 / URI 1.71: CVE-2026-8368 (Authorization leaked on redirect), CVE-2023-31486, CVE-2026-7010, CVE-2026-7017, CVE-2026-19953. Outbound calls (Turnstile, OAuth, MapIt, geocoders) need an attacker-controlled redirect; low-medium. Fix: URI 5.40 and HTTP::Tiny >=0.095 (master pins only 0.090, still below 0.095).
- MEDIUM Net::DNS 1.33: CVE-2026-64193 (critical in feed), CVE-2026-64194, CVE-2026-81928. Used for email-domain validation of attacker-supplied addresses, so attacker-controlled DNS responses are parsed. Plausible exposure; details unread. Fix: >=1.57 (master has it).
- MEDIUM DBI 1.623: 20+ CVEs (CVE-2020-14392/14393, CVE-2026-78030 critical "load arbitrary modules", CVE-2026-88816 high). Mostly DBD::File/ProfileData/driver attributes; we use DBD::Pg with bound parameters. Low practical exposure. Fix: >=1.656.
- MEDIUM Net::OAuth 0.28: CVE-2025-22376, CVE-2026-72887/72888/72889/75589. Only the OAuth1/Twitter path; our social login is GreeceSocial.pm. Probably unused. Fix: >=0.33.
- LOW Crypt::OpenSSL::RSA 0.33 CVE-2024-2467 (Marvin timing; fix 0.35): not exploitable for signing/verifying.
- LOW CryptX 0.069 (CVE-2025-40914, CVE-2026-41564), Crypt::CBC (CVE-2025-2814), JSON::XS 4.02 (CVE-2025-40928), Cpanel::JSON::XS 3.0210 (CVE-2025-40929): integer overflows on huge inputs; nginx limits body size.
- LOW Authen::SASL 2.16 (CVE-2025-40918, CVE-2026-86219): DIGEST-MD5 not used. Mozilla::CA 20211001 (CVE-2024-39689, CVE-2026-113812): stale CA bundle.
- LOW HTML::Parser 3.69 (CVE-2026-8829), XML::LibXML 2.0132 (CVE-2026-8177), XML::Simple 2.20, XML::Parser 2.41, YAML 1.28 (CVE-2017-20285), CGI::Simple, HTTP::Date, Web::Simple, FCGI 0.74 (CVE-2025-40907), Plack 1.0047 (CVE-2026-7381 XSendfile, not enabled): need hostile XML/YAML/headers we do not accept from the public as far as I saw (unverified).
- INFO no CPANSA hit: Catalyst 5.90124, Moose, DBIx::Class 0.082841, Email::Address 1.912, Text::CSV 1.99, Net::Server 2.009.
- Not checkable: Perl 5.32.1 core (trivy shows no fixable HIGH/CRITICAL for perl, but bullseye support is over).

## 3. Vendored JavaScript (running image = v6.0 files; version strings and osv.dev API)

- MEDIUM MapLibre GL JS 4.7.1 (web/cobrands/greece/vendor/maplibre-gl-4.7.1): GHSA-jrc7-96c5-q579 / CVE-2026-85061 XSS sanitizer bypass in DOM.sanitize() (fixed 6.4.1). Exploitable only if untrusted HTML reaches popups/attribution through the sanitizer; our popups are built by our code, so low unless report text is shown in popups (unsure). Fix: >=6.4.1 and retest the Greek map.
- MEDIUM jQuery UI 1.12.1 (web/vendor/jquery-ui.min.js): CVE-2021-41182, CVE-2021-41183 (datepicker XSS), CVE-2021-41184 (.position `of`), CVE-2022-31160 (checkboxradio). Option values come from our code, not users; I did not confirm which Greek pages load it. Fix: 1.13.2+.
- INFO jQuery 3.6.0 (master 3.7.1): none known. jquery-validation 1.21.0: none known.
- LOW Dropzone 5.1.1 (version string in dropzone.min.js, not fully certain): osv.dev none; old (2016); used on photo upload.
- LOW OpenLayers 2.14-dev builds (OpenLayers.*.js): OL2 is end-of-life, no advisory feed; Greek map still loads OpenLayers.wfs.js and map-OpenLayers.js.
- INFO Fancybox 1.3.4 (ancient, unmaintained), html5sortable, jquery.multi-select, Chart.js fork, accessible-autocomplete, uFuzzy 1.0.11, lite-youtube-embed, modernizr 3.11.4, idb-keyval, history.polyfill 4.2.7: no osv hits for those with package names.
- Not checked: internals of the Chart.js fork and OL2 beyond version strings.

## 4. Python helper services

- docker/greece/anonymiser (FROM python:3.12-slim, floating): requirements.txt pins 10 direct packages (fast-alpr 0.4.0, fast-plate-ocr 1.1.0, flatbuffers 25.12.19, numpy 2.2.6, onnxruntime 1.31.0, open-image-models 0.6.0, opencv-python-headless 4.12.0.88, protobuf 7.36.2, PyYAML 6.0.3, nudenet 3.4.2). Transitive deps unpinned, no hashes. osv-scanner reported transitive pygments 2.9.0 (PYSEC-2023-117, PYSEC-2026-2987) and tqdm 4.9.0 (PYSEC-2017-74, PYSEC-2026-1976), but that looks like a lowest-version guess; trivy on the built image found 0 HIGH/CRITICAL in Python packages (Debian 13.7 base). Severity low/info.
  - MEDIUM: runs as ROOT (no USER) while parsing untrusted public images (OpenCV/onnx). Fix: non-root USER, read-only rootfs, cap_drop ALL.
  - LOW-MEDIUM supply chain: YuNet model fetched from github.com/opencv_zoo/raw/main (floating branch) but sha256-verified (good); ALPR models are downloaded by fast_alpr at build time with NO hash check. ONNX files, not pickles (safer). Fix: vendor and hash them. apt packages unpinned.
- docker/greece/video (FROM debian:bookworm-slim): stdlib Python plus apt ffmpeg; runs as uid 1000 fmsvideo (good); trivy clean at scan time. ffmpeg parses untrusted video: rebuild often; compose already limits mem 768m, 2 cpus. No requirements.txt, nothing to pin. Low.
- docker/mapit-local (python:3.12-slim, shapely==2.0.7, USER nobody): trivy clean. Info.

## 5. Docker base images and OS

- HIGH fixmystreet/fixmystreet:stable -> fixmystreets-gr (Debian 11.7 bullseye, packages from 2024-11): Debian 11 LTS ended 2026-08-31, no more security updates. Trivy (fix available only): 99 CRITICAL + 1,177 HIGH. Notable: ImageMagick 6.9.11 (13 CRITICAL e.g. CVE-2025-53014, CVE-2025-53101, CVE-2025-57807, CVE-2026-23876 XBM code execution, CVE-2026-25897, CVE-2026-25968; dozens of HIGH incl. CVE-2026-25965 local file disclosure); openssl/libssl1.1 (CVE-2025-69421, CVE-2026-28387 ..; OpenSSL 1.1.1 EOL); libxml2 2.9.10 (CVE-2024-56171, CVE-2025-24928 ..); libpq5 13.17 (CVE-2025-1094, CVE-2025-8714/8715, CVE-2026-2004); sudo (CVE-2025-32462, CVE-2026-35535). ImageMagick is reachable: perllib/FixMyStreet/ImageMagick.pm processes uploaded photos; the policy.xml only blocks mpeg/HTTP/filters. Photos pass the anonymiser first but I did not verify Perl only ever sees a re-encoded JPEG, so treat it as reachable. Fix: new base (Debian 12/13) with FMS installed from a pinned commit; restrict ImageMagick policy to jpeg/png/webp/gif; re-encode uploads in the anonymiser before Perl.
- HIGH app container configuration: runs as root with systemd as PID 1, `cgroup: host`, /sys/fs/cgroup mounted rw, stop_signal SIGRTMIN+3, default capability set (CapEff a80425fb), not privileged. App workers run as `fms` (good). An app compromise lands in a root container with a writable host cgroup tree: higher escape risk than normal. Fix: run Starman directly as fms, drop cgroup host, cap_drop ALL, no-new-privileges, read-only rootfs.
- HIGH postgres:13.11 (Debian 12.1): PostgreSQL 13 went EOL 2025-11-13; 13.11 is from mid-2023, missing about ten minor releases (e.g. CVE-2024-0985, CVE-2025-1094, CVE-2025-8714). Trivy 21 CRITICAL / 158 HIGH (perl, gosu Go stdlib, libs). Internal network only, no published ports. Fix: move to a supported major via dump/restore, pin minor and digest. Compose builds it inline and docker/Dockerfile-postgres duplicates it.
- MEDIUM nginx:1.27.2 (Debian 12.8): reachable only via cloudflared on 127.0.0.1:8000. Trivy 11 CRITICAL / 88 HIGH, mostly libs off the nginx path; lacks later fixes (e.g. CVE-2025-23419 fixed in 1.27.4, needs client certs, not used). Fix: current stable pinned by digest.
- MEDIUM memcached:1.6.32: 6 CRITICAL / 36 HIGH in base libs; internal network, no auth. Fix: update.
- MEDIUM maptiler/tileserver-gl v5.6.0 (Ubuntu 24.04, user node): 26 CRITICAL (linux-libc-dev headers, irrelevant) plus Node: tar CVE-2026-59873, handlebars CVE-2026-106445/6, proxy-addr CVE-2026-90711, maplibre-gl 5.22.0 CVE-2026-85061. Public via /tiles/. Fix: newer tag.
- MEDIUM floating tags: fixmystreet/fixmystreet:stable (stale), python:3.12-slim, debian:bookworm-slim; fixed tags (nginx, memcached, tileserver, postgres) are pinned but old and not by digest.
- LOW python/debian slim images were fresh at last build (trivy clean) but only update when someone rebuilds.
- INFO root /Dockerfile (jgoerzen/debian-base-standard:bullseye) is upstream's, not used for our build. Planetiler image present locally, build tool only.

## 6. Secret scanning (both repos, full history)

Method: gitleaks over all history of the public clone and a --mirror of the private repo (all branches incl. backup/pre-public-20261024); custom regexes over every added line in the Greece-era range of both (private keys, Turnstile 0x4AAAA, Google GOCSPX/AIza, AWS, JWT, DB URLs with password, Slack/GitHub tokens, Cloudflare keys, Microsoft client secrets, password/token assignments, SMTP creds, Greek phone numbers, free-mail addresses, private IPs); file-history check for .env, general.yml-local, *.pem/*.key/*.p12/*.jks. Values are not printed.

- INFO (good) No private keys, cloud/API keys, JWTs, DB-URL passwords, Turnstile/Google/Microsoft/Apple client secrets or SMTP credentials in Greece-era commits of either repo.
- INFO gitleaks: 66 generic-api-key hits in EACH repo, all in upstream mySociety files (tests, council tracking-code templates, cookieconsent vendor, MapTiler/Cheshire East map keys, ubuntu-xenial-16.04-cloudimg-console.log). None in Greek files. Do not reuse mySociety's MapTiler key.
- INFO GreeceSocial.pm hits are false positives (OAuth endpoint URLs; secrets are read from config).
- INFO (good) conf/general.yml-local, docker/.env and /.env are in .gitignore (git check-ignore confirms) with 0 commits in either history. On the fms VM: general.yml-local mode 0640, .env mode 0600.
- LOW compose passes POSTGRES_PASSWORD and the superuser password to the app container as environment variables (visible to root via docker inspect).
- PRIVATE repo only: data/greece/** (municipal/police contact emails and phone numbers: departments.csv, dimoi*.sql/csv, police*.csv, haidari.sql ...), docs/greece/gdpr/*.md, bin/greece/mail-delivery and departments-review (private 10.x/192.168.x addresses). Correct to keep private. I could not verify the GitHub repo RaNd250/fixmystreets is actually private.
- Public repo review: bin/greece/publish-public.sh whitelists paths and greps for keys, uns.gr, vitaldata, 10.0.201., 192.168., @fixmystreets.gr; my grep found no internal hostnames/IPs in the public tree (only upstream Vagrantfile comment). Public data/greece/contacts/digest.sql and votes.sql are schema/logic only.
- LOW (privacy) public web/cobrands/greece/dimoi/index.json holds each municipality's contact address; 15 of 332 entries use free-mail addresses (10 gmail, 5 yahoo.gr; e.g. Agios Nikolaos, West Samos, Ermionida, Karpathos, Chaidari). They may be personal mailboxes of staff. Likely taken from official sites, but confirm; consider removing or serving via the app only. The file is also shipped to every visitor.
- INFO identities: public history shows only "VitalData Services <noreply@fixmystreets.gr>"; private shows RaNd250 GitHub noreply plus two "Claude <noreply@anthropic.com>" commits. No real email addresses. Make sure backup/pre-public-20261024 is never pushed to the public remote.

## 7. Licensing and supply chain

- LOW upstream root Dockerfile fetches install-site.sh from raw.githubusercontent.com/mysociety/commonlib/master (unpinned, run as root at build); not our Dockerfile but our image inherits its result. Our docker/greece/Dockerfile: floating base plus sed/locale-gen only.
- LOW-MEDIUM anonymiser model downloads without hash, unpinned transitive pip deps (section 4). No curl|sh in our Dockerfiles. apt installs unpinned.
- LOW GitHub Actions in the public fork (.github/workflows: coverage, cypress, default, docs) are upstream's and trigger on push/pull_request; they use floating refs (Wandalen/wretry.action@master, actions/cache@v3) and CODECOV_TOKEN/CYPRESS_RECORD_KEY secrets (absent in the fork, so inert). Fix: delete or disable Actions in the fork.
- INFO no git hooks installed on the fms VM repo (samples only). Submodule URLs (git://git.mysociety.org/commonlib, mysociety docs theme) are unauthenticated git://, build-time only, not checked out.
- INFO Licence: FixMyStreet is AGPL-3.0; the footer offers source via the public fork, which matches the running code (v6.0); publish-public.sh supports that. The anonymiser, mapit-local, tiles and nginx config are separate programs and are deliberately private. Unverified: licence of the downloaded ALPR model weights (yolo-v9-t-384-license-plate-end2end, cct-xs-v2-global-model; YOLO-derived weights can carry AGPL/GPL terms), please check. MapLibre BSD-3, jQuery MIT, Dropzone MIT, OpenLayers 2 BSD-2.

## 8. Other notable

- INFO nginx/limits trust the CF-Connecting-IP header; nginx binds 127.0.0.1/::1 only, so only local processes (cloudflared) can set it. Good.
- INFO container logs rotate 3x10 MB (privacy requirement). Good.
- LOW docker/Dockerfile-postgres duplicates the compose inline build.
- Not checked: contents of conf/general.yml-local (not read), which Greek pages load jquery-ui, whether the Greek Perl uses Net::OAuth/Crypt::JWT, TLS/HTTP headers (other review), the 1,689 upstream commits individually.

## Priority fix order
1. Rebuild the app image on a supported base from a pinned upstream commit with the upgraded cpanfile.snapshot (fixes Session CVE-2025-40924, EncodedColumn, FormHandler, Starman, ImageMagick, openssl, libxml2, Debian EOL). Stop using :stable.
2. App container: no systemd/root/host cgroup; non-root, dropped caps. Anonymiser: non-root USER.
3. Upgrade PostgreSQL 13.11 (EOL) to a supported major.
4. MapLibre >=6.4.1, jQuery UI 1.13.2+; refresh nginx/memcached/tileserver pins by digest.
5. Hash-verify ALPR models; review the 15 free-mail municipal addresses in the public dimoi/index.json; disable upstream Actions in the fork.

## Counts
critical 0; high 4 (stale Debian 11 image incl. ImageMagick; Catalyst::Plugin::Session CVE-2025-40924; app container root/systemd/host cgroup; PostgreSQL 13.11 EOL); medium about 17; low about 13; info about 12. No critical because nothing found is confirmed remotely exploitable without further conditions; ImageMagick and Session could rise to critical after exploit validation.
