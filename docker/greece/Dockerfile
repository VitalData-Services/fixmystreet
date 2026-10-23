# FixMyStreets Ελλάδα: the upstream image with the Greek system locale generated.
# Without el_GR.UTF-8, setlocale() fails and every string falls back to English,
# even with a complete el_GR FixMyStreet.mo in place.
FROM fixmystreet/fixmystreet:stable
USER root
RUN sed -i 's/^# *el_GR.UTF-8 UTF-8/el_GR.UTF-8 UTF-8/' /etc/locale.gen && locale-gen
