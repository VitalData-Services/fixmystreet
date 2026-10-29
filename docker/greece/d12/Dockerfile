# FixMyStreets Ελλάδα on Debian 12. The same FixMyStreet v6.0 tree as the Debian 11 image (fixmystreets-gr:pre-d12),
# put on the Debian 12 version of the upstream base (jgoerzen/debian-base-standard) with Perl 5.36, and its Perl modules built
# again for it from cpanfile.snapshot. What the upstream Dockerfile and install-site.sh do is repeated here by hand,
# because upstream has no Debian 12 image. Build: docker build -t fixmystreets-gr:d12 -f docker/greece/d12/Dockerfile docker/greece/d12
FROM fixmystreets-gr:pre-d12 AS old

FROM jgoerzen/debian-base-standard:bookworm
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get -qq update \
 && apt-get -qq -y install ca-certificates sudo apt-utils git locales lockfile-progs curl wget dnsutils lsb-release gnupg debconf \
 && printf 'en_GB.UTF-8 UTF-8\nel_GR.UTF-8 UTF-8\ncy_GB.UTF-8 UTF-8\nsv_SE.UTF-8 UTF-8\nde_CH.UTF-8 UTF-8\n' >> /etc/locale.gen \
 && locale-gen \
 && printf 'LANG="en_GB.UTF-8"\nLC_ALL="en_GB.UTF-8"\n' > /etc/default/locale

RUN echo postfix postfix/main_mailer_type select 'Internet Site' | debconf-set-selections \
 && echo postfix postfix/mail_name string 127.0.0.1.xip.io | debconf-set-selections \
 && apt-get -qq -y install postfix

# The packages of conf/packages.docker (ttf-bitstream-vera is fonts-dejavu-core now), and what the Perl modules build with.
RUN apt-get -qq -y install make g++ jhead liblocale-gettext-perl libpng-dev perl perlmagick libmath-bigint-gmp-perl gettext \
      postgresql-server-dev-all postgresql-client gnuplot fonts-dejavu-core libexpat1-dev libssl-dev zlib1g-dev libxml2-dev libreadline-dev \
      libyaml-dev libgmp-dev pkg-config libjpeg-dev

RUN adduser --quiet --disabled-password --gecos "A user for the site fixmystreet" --uid 1000 fms

COPY --from=old --chown=fms:fms /var/www/fixmystreet/fixmystreet /var/www/fixmystreet/fixmystreet
COPY --from=old --chown=fms:fms /var/www/fixmystreet/install-site.sh /var/www/fixmystreet/last-host /var/www/fixmystreet/install-arguments /var/www/fixmystreet/
COPY --from=old /etc/init.d/fixmystreet /etc/init.d/fixmystreet
COPY --from=old /etc/sudoers.d/10_fms_install_packages /etc/sudoers.d/10_fms_install_packages
COPY --from=old --chown=fms:crontab /var/spool/cron/crontabs/fms /var/spool/cron/crontabs/fms

RUN mkdir -p /var/www/fixmystreet/logs && chown fms:fms /var/www/fixmystreet/logs \
 && chmod 0440 /etc/sudoers.d/10_fms_install_packages && chmod 0600 /var/spool/cron/crontabs/fms && chmod a+rx /etc/init.d/fixmystreet \
 && update-rc.d fixmystreet defaults \
 && ln -s /var/www/fixmystreet/fixmystreet /home/fms/fixmystreet \
 && cp /var/www/fixmystreet/fixmystreet/bin/docker.preinit /usr/local/preinit/99-fixmystreet && chmod +x /usr/local/preinit/99-fixmystreet

# The Perl modules again, for Perl 5.36 (the old ones are compiled for 5.32), then Catalyst::Plugin::Session 0.44 (CVE-2025-40924).
RUN su fms -c 'cd /var/www/fixmystreet/fixmystreet && rm -rf local && bin/install_perl_modules' \
 && su fms -c 'cd /var/www/fixmystreet/fixmystreet && bin/cpanm --notest -l local Catalyst::Plugin::Session@0.44'

RUN apt-get purge -y --auto-remove make g++ libexpat1-dev libssl-dev zlib1g-dev libxml2-dev postgresql-server-dev-all libyaml-dev libgmp-dev libjpeg-dev libpng-dev libreadline-dev || true \
 && apt-get -y clean && rm -fr /var/lib/apt/lists/* /home/fms/.cpanm/*

EXPOSE 9000
CMD ["/usr/local/bin/boot-debian-base"]
