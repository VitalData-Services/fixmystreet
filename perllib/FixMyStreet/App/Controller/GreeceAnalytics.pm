package FixMyStreet::App::Controller::GreeceAnalytics;
use Moose;
use namespace::autoclean;
BEGIN { extends 'Catalyst::Controller'; }
use DateTime;

=head1 NAME

FixMyStreet::App::Controller::GreeceAnalytics - /admin/greece/analytics: visitors and reports at a glance (Greece cobrand)

=head1 DESCRIPTION

  GET /admin/greece/analytics   the last 30 days: visitors (people and robots apart), reports, new accounts,
                                the most viewed pages and where visitors came from (last 7 days), the reports
                                by state and by municipality, and what waits for approval.

Visitor counts come from bin/greece/visits-aggregate (hourly, from nginx's access log): daily counts only,
nothing that names a visitor, no third-party tracker. Report and account counts are read live from the
database. Superusers only; the second sign-in step (greece_2fa_gate) applies as everywhere.

=cut

my $TZ = 'Europe/Athens';
my $DAYS = 30;

sub analytics : Path('/admin/greece/analytics') : Args(0) {
    my ( $self, $c ) = @_;
    $c->detach('/page_error_404_not_found', []) unless $c->cobrand->moniker eq 'greece';
    return $c->res->redirect('/auth?r=/admin/greece/analytics') unless $c->user_exists;
    $c->detach('/page_error_403_access_denied', ['']) unless $c->user->is_superuser;

    my $dbh = $c->model('DB')->schema->storage->dbh;
    my $today = DateTime->now( time_zone => $TZ )->truncate( to => 'day' );
    my @days = map { $today->clone->subtract( days => $DAYS - 1 - $_ )->ymd } 0 .. $DAYS - 1;
    my %row = map { $_ => { day => $_, people => 0, robots => 0, visitors => 0, bots_seen => 0, reports => 0, users => 0 } } @days;

    # Visitors (may not exist until bin/greece/visits-aggregate has run once).
    my ( $have_visits, $counted_to ) = ( 0, undef );
    eval {
        local $dbh->{RaiseError} = 1;
        for my $r ( @{ $dbh->selectall_arrayref(
            "SELECT day::text, kind, pageviews, uniques FROM greece_visits_daily WHERE day >= ?::date", undef, $days[0] ) } ) {
            my $d = $row{ $r->[0] } or next;
            if ( $r->[1] eq 'people' ) { $d->{people} = $r->[2]; $d->{visitors} = $r->[3] }
            else                       { $d->{robots} = $r->[2]; $d->{bots_seen} = $r->[3] }
        }
        ($counted_to) = $dbh->selectrow_array("SELECT to_char(last_hour AT TIME ZONE '$TZ', 'DD/MM/YYYY HH24:MI') FROM greece_visits_state WHERE id = 1");
        $have_visits = 1 if $counted_to;
        $c->stash->{top_pages} = $dbh->selectall_arrayref(
            "SELECT path, sum(views)::int FROM greece_visits_pages WHERE day > ?::date - 7 + 1 GROUP BY path ORDER BY 2 DESC, 1 LIMIT 12",
            undef, $days[-1] );
        $c->stash->{top_refs} = $dbh->selectall_arrayref(
            "SELECT host, sum(views)::int FROM greece_visits_ref WHERE day > ?::date - 7 + 1 GROUP BY host ORDER BY 2 DESC, 1 LIMIT 10",
            undef, $days[-1] );
    };
    $dbh->rollback if $@ && !$dbh->{AutoCommit};

    # Reports and accounts per day.
    for my $r ( @{ $dbh->selectall_arrayref(
        "SELECT (created AT TIME ZONE 'UTC' AT TIME ZONE '$TZ')::date::text, count(*) FROM problem
          WHERE created >= ?::date - 1 AND state <> 'hidden' GROUP BY 1", undef, $days[0] ) } ) {
        $row{ $r->[0] }{reports} = $r->[1] if $row{ $r->[0] };
    }
    for my $r ( @{ $dbh->selectall_arrayref(
        "SELECT (created AT TIME ZONE 'UTC' AT TIME ZONE '$TZ')::date::text, count(*) FROM users
          WHERE created >= ?::date - 1 GROUP BY 1", undef, $days[0] ) } ) {
        $row{ $r->[0] }{users} = $r->[1] if $row{ $r->[0] };
    }

    # Bars: each series scaled to its own maximum (percent, at least 2 for a non-zero value).
    my $series = sub {
        my $key = shift;
        my $max = 0;
        for (@days) { $max = $row{$_}{$key} if $row{$_}{$key} > $max }
        $row{$_}{ $key . '_pct' } = !$max ? 0 : $row{$_}{$key} ? ( int( 100 * $row{$_}{$key} / $max ) || 2 ) : 0 for @days;
        return $max;
    };
    my %max = map { $_ => $series->($_) } qw(people robots visitors reports users);

    my $sum = sub { my $k = shift; my $t = 0; $t += $row{$_}{$k} for @days; $t };

    # Reports by state, top municipalities, waiting for approval.
    my $by_state = $dbh->selectall_arrayref(
        "SELECT state, count(*) FROM problem WHERE state <> 'hidden' GROUP BY state ORDER BY 2 DESC, 1" );
    my $by_body = $dbh->selectall_arrayref(<<'SQL');
SELECT b.name, count(*) FROM body b
 JOIN problem p ON b.id::text = ANY(string_to_array(p.bodies_str, ','))
 WHERE NOT b.deleted AND p.state <> 'hidden' AND NOT p.non_public
 GROUP BY b.name ORDER BY 2 DESC, 1 LIMIT 10
SQL
    my $cobrand = $c->cobrand;
    my $waiting = scalar grep { $cobrand->greece_needs_approval($_) } $c->model('DB::Problem')->search({
        state => [ FixMyStreet::DB::Result::Problem->open_states ],
        send_state => 'unprocessed',
        whensent => undef,
        bodies_str => { '!=' => undef },
    })->all;
    my ($reports_total) = $dbh->selectrow_array("SELECT count(*) FROM problem WHERE state <> 'hidden'");
    my ($users_total)   = $dbh->selectrow_array("SELECT count(*) FROM users");
    my ($today_people)  = ( $row{ $days[-1] }{visitors} );

    $c->stash(
        template => 'admin/greece_analytics.html',
        days => [ map { $row{$_} } @days ],
        max => \%max,
        have_visits => $have_visits,
        counted_to => $counted_to,
        period_days => $DAYS,
        total_people => $sum->('people'),
        total_robots => $sum->('robots'),
        total_reports => $sum->('reports'),
        total_users => $sum->('users'),
        by_state => $by_state,
        by_body => $by_body,
        waiting => $waiting,
        reports_all => $reports_total,
        users_all => $users_total,
        today_visitors => $today_people,
    );
}

__PACKAGE__->meta->make_immutable;

1;
