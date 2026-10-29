# FixMyStreets Ελλάδα: the upstream image with the Greek system locale generated.
# Without el_GR.UTF-8, setlocale() fails and every string falls back to English,
# even with a complete el_GR FixMyStreet.mo in place.
FROM fixmystreet/fixmystreet:stable
USER root
RUN sed -i 's/^# *el_GR.UTF-8 UTF-8/el_GR.UTF-8 UTF-8/' /etc/locale.gen && locale-gen

# Security updates of the base. Debian 11 has left the main mirrors (its security updates are served from
# archive.debian.org now): ImageMagick, OpenSSL, libc, Perl and the rest, and Catalyst::Plugin::Session 0.44
# (CVE-2025-40924: guessable session ids in 0.37). The base image is from 2024-11; a rebuild on a newer upstream and
# Debian 12 is a separate step (docs/greece/SECURITY-REVIEW.md).
RUN sed -i 's#http://deb.debian.org/debian-security#http://archive.debian.org/debian-security#; s#http://deb.debian.org/debian#http://archive.debian.org/debian#' /etc/apt/sources.list.d/* /etc/apt/sources.list 2>/dev/null; \
    echo 'Acquire::Check-Valid-Until false;' > /etc/apt/apt.conf.d/99archive \
 && apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y upgrade \
 && apt-get -y install --no-install-recommends cpanminus make \
 && cpanm --notest -l /var/www/fixmystreet/fixmystreet/local Catalyst::Plugin::Session@0.44 \
 && apt-get -y purge cpanminus make && apt-get -y autoremove && apt-get clean && rm -rf /var/lib/apt/lists/* /root/.cpanm
