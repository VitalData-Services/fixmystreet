package FixMyStreet::Cobrand::Greece;
use base 'FixMyStreet::Cobrand::Default';

use strict;
use warnings;
use utf8;

# Reuse the Default cobrand's compiled CSS; this cobrand only adds templates and a little JS/CSS.
sub asset_moniker { 'default' }

# Search box: "ref: 123" (database id) or a public reference "DDMMYYYY-N".
# A bare number stays a place search, because Greek postcodes are five digits.
sub lookup_by_ref_regex { qr/^\s*(?|ref:\s*(\d+)|(\d{8}-\d+))\s*$/ }

sub lookup_by_ref {
    my ($self, $ref) = @_;
    return unless $ref =~ /^(\d\d)(\d\d)(\d{4})-(\d+)$/;
    my $id = FixMyStreet::DB::Result::Problem::greece_ref_to_id("$3-$2-$1", $4);
    return [ id => $id || 0 ];
}

# Values the report email templates use besides the stock ones.
sub munge_sendreport_params {
    my ($self, $row, $h, $params) = @_;

    # The address the email went to, so the recipient can send us a better one.
    $h->{sent_to} = join ', ', map { ref $_ ? $_->[0] : $_ } @{ $params->{To} || [] };

    # A category can have its own email (contact extra metadata email_template, e.g. "amea"
    # for the police complaint about disabled or EV-charging bays); submit.txt hands over to it.
    my $contact = $row->contact;
    my $template = ($contact && $contact->get_extra_metadata('email_template')) || '';
    $h->{email_template} = $template if $template =~ /^[a-z]+$/;

    # The municipality of the location, for emails to a body that is not the municipality.
    my $dimos = $row->greece_dimos;
    $h->{dimos_name} = $dimos->name if $dimos;
}

# Police complaints (disabled and EV-charging bays) can also be sent by the reporter as an SMS
# from their own phone; see Problem::greece_sms.
sub greece_sms_number { '100' }

package FixMyStreet::DB::Result::Problem;

use strict;
use warnings;
use utf8;

# The municipality body covering the report's location.
sub greece_dimos {
    my $self = shift;
    my @areas = grep { $_ } split /,/, ($self->areas || '');
    return unless @areas;
    return FixMyStreet::DB->resultset('Body')->search(
        { 'body_areas.area_id' => \@areas, 'me.name' => { -like => 'Δήμος %' }, 'me.deleted' => 0 },
        { join => 'body_areas', order_by => 'me.id' })->first;
}

# For a police complaint, the SMS the reporter can send from their phone: { number, body }.
# The body names the violation (as worded in the category's question), the place and the
# vehicle, and gives the report reference. Nothing for other categories.
sub greece_sms {
    my ($self, $cobrand) = @_;
    my $contact = $self->contact;
    return unless $contact && ($contact->get_extra_metadata('email_template') || '') eq 'amea';

    my %answer = map { $_->{name} => $_->{value} } @{ $self->get_extra_fields };
    my ($question) = grep { $_->{code} eq 'paravasi' } @{ $contact->get_extra_fields };
    my ($choice) = grep { $_->{key} eq ($answer{paravasi} // '') } @{ $question ? $question->{values} || [] : [] };
    my $violation = $choice ? $choice->{name} : 'Παράνομη στάθμευση σε θέση ΑμεΑ ή φόρτισης ηλεκτρικών οχημάτων';

    my $address = $cobrand ? $cobrand->find_closest($self) : FixMyStreet::Geocode::Address->new($self->geocode);
    my $parts = $address->parts;
    my $osm = $address->{address} || {};
    my $place = $osm->{suburb} || $osm->{neighbourhood} || $osm->{city} || $osm->{town} || $osm->{village};
    unless ($place) {
        my $dimos = $self->greece_dimos;
        ($place = $dimos->name) =~ s/^Δήμος // if $dimos;
    }
    my $where = join ', ', grep { $_ } join(' ', grep { $_ } $parts->{street}, $parts->{number}), $place;
    my $coords = sprintf '%.5f, %.5f', $self->latitude, $self->longitude;

    my @lines = ("Καταγγελία: $violation.");
    push @lines, 'Θέση: ' . ($where ? "$where ($coords)" : $coords) . '.';
    (my $vehicle = $answer{oxima} // '') =~ s/^\s+|\s+$//g;
    push @lines, "Όχημα: $vehicle." if $vehicle;
    (my $site = FixMyStreet->config('BASE_URL')) =~ s{^https?://}{};
    push @lines, 'Αρ. αναφοράς ' . $self->greece_ref . " ($site).";
    return { number => FixMyStreet::Cobrand::Greece->greece_sms_number, body => join("\n", @lines) };
}

# Public reference DDMMYYYY-N: the local (TIME_ZONE) date the report was created and its
# position among all reports created that day. `created` holds wall-clock time in the
# server's zone, because FixMyStreet sets the DB session time zone to it.

sub _greece_zones {
    return (FixMyStreet->local_time_zone->name, (FixMyStreet->time_zone || FixMyStreet->local_time_zone)->name);
}

sub greece_ref {
    my $self = shift;
    return $self->{__greece_ref} //= do {
        my ($server_tz, $site_tz) = _greece_zones();
        my $dbh = $self->result_source->schema->storage->dbh;
        # Placeholders bind in text order: CTE (site, server, id), then each day bound (server, site).
        my ($day, $n) = $dbh->selectrow_array(<<'SQL', undef, $site_tz, $server_tz, $self->id, $server_tz, $site_tz, $server_tz, $site_tz);
WITH p AS (
    SELECT id, timezone(?, timezone(?, created)) AS local_created FROM problem WHERE id = ?
)
SELECT to_char(p.local_created, 'DDMMYYYY'),
       (SELECT count(*) FROM problem q
         WHERE q.id <= p.id
           AND q.created >= timezone(?, timezone(?, date_trunc('day', p.local_created)))
           AND q.created <  timezone(?, timezone(?, date_trunc('day', p.local_created) + interval '1 day')))
FROM p
SQL
        defined $day ? "$day-$n" : $self->id;
    };
}

# Every photo of the report at full size, for attaching to an email.
sub greece_photos {
    my $self = shift;
    my $set = $self->get_photoset;
    return [ grep { $_ } map { $set->get_image_data(num => $_, size => 'full') } 0 .. $set->num_images - 1 ];
}

# When the report was made, in local time, e.g. "24/10/2026 18:05".
sub greece_local_time {
    my $self = shift;
    my $dt = ($self->confirmed || $self->created)->clone;
    $dt->set_time_zone(FixMyStreet->local_time_zone) if $dt->time_zone->is_floating;
    $dt->set_time_zone(FixMyStreet->time_zone || FixMyStreet->local_time_zone);
    return $dt->strftime('%d/%m/%Y %H:%M');
}

# Inverse of greece_ref: the id of the $n-th report created on local date $date (YYYY-MM-DD).
sub greece_ref_to_id {
    my ($date, $n) = @_;
    return unless $n >= 1;
    my ($server_tz, $site_tz) = _greece_zones();
    my $dbh = FixMyStreet::DB->schema->storage->dbh;
    my $id = eval {
        $dbh->selectrow_array(<<'SQL', undef, $server_tz, $site_tz, $date, $server_tz, $site_tz, $date, $n - 1);
SELECT id FROM problem
 WHERE created >= timezone(?, timezone(?, ?::date::timestamp))
   AND created <  timezone(?, timezone(?, ?::date::timestamp + interval '1 day'))
 ORDER BY id OFFSET ? LIMIT 1
SQL
    };
    return $id;
}

1;
