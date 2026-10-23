package FixMyStreet::Cobrand::Greece;
use base 'FixMyStreet::Cobrand::Default';

use strict;
use warnings;

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

package FixMyStreet::DB::Result::Problem;

use strict;
use warnings;

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
