package FixMyStreet::App::Controller::GreeceSitemap;
use Moose;
use namespace::autoclean;
BEGIN { extends 'Catalyst::Controller'; }

use Encode ();
use URI::Escape qw(uri_escape_utf8);

=head1 NAME

FixMyStreet::App::Controller::GreeceSitemap - /sitemap.xml, always current (Greece cobrand)

=head1 DESCRIPTION

The home, help, about and reports pages, each municipality's reports page that has public reports
(/reports/<name>, spaces as '+', the address FixMyStreet names as canonical, with the date of its latest
change) and each public report (/report/<number>, as the report's own page names it). A report that is
hidden, private, flagged out of public view or not yet confirmed is not listed. nginx hands
/sitemap.xml to this address (the app's static files would answer /sitemap.xml itself); web/sitemap.xml stays as the file the stock setup would serve.

=cut

my @PAGES = (
    [ '/',              'daily',   '1.0' ],
    [ '/reports',       'daily',   '0.8' ],
    [ '/faq',           'monthly', '0.6' ],
    [ '/about',         'monthly', '0.5' ],
    [ '/about/foreis',  'monthly', '0.4' ],
    [ '/about/privacy', 'yearly',  '0.3' ],
    [ '/about/terms',   'yearly',  '0.3' ],
);

sub sitemap : Path('/greece/sitemap.xml') : Args(0) {
    my ( $self, $c ) = @_;
    my $cobrand = $c->cobrand;
    if ( $cobrand->moniker ne 'greece' ) { $c->detach('/page_error_404_not_found') }

    my $base = $cobrand->base_url;
    my @out = (
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    );
    my $url = sub {
        my ( $path, $freq, $prio, $lastmod ) = @_;
        push @out, '  <url><loc>' . _xml( $base . $path ) . '</loc>'
            . ( $lastmod ? "<lastmod>$lastmod</lastmod>" : '' )
            . "<changefreq>$freq</changefreq><priority>$prio</priority></url>";
    };
    $url->( @$_ ) for @PAGES;

    my $rows = $c->model('DB')->schema->storage->dbh->selectall_arrayref(<<'SQL');
SELECT b.name, max(p.lastupdate)::date FROM body b
 JOIN problem p ON b.id::text = ANY(string_to_array(p.bodies_str, ','))
 WHERE NOT b.deleted AND b.name LIKE 'Δήμος %' AND NOT p.non_public
   AND p.state NOT IN ('unconfirmed', 'hidden', 'partial')
 GROUP BY b.name ORDER BY b.name
SQL
    for my $r (@$rows) {
        ( my $name = $r->[0] ) =~ s/ /+/g;
        $url->( '/reports/' . uri_escape_utf8($name, '^A-Za-z0-9\-_.~+'), 'weekly', '0.5', $r->[1] );
    }

    my $problems = FixMyStreet::DB->resultset('Problem')->search(
        { non_public => 0, state => { -not_in => [ 'unconfirmed', 'hidden', 'partial' ] } },
        { order_by => { -desc => 'lastupdate' }, rows => 45000 } );
    while ( my $p = $problems->next ) {
        $c->cobrand->greece_report_indexable($p) or next;
        my $path = $p->url or next;
        ( my $day = $p->lastupdate . '' ) =~ s/[ T].*//;
        $url->( $path, 'weekly', '0.4', $day );
    }
    push @out, '</urlset>', '';

    $c->res->content_type('application/xml; charset=utf-8');
    $c->res->header( 'Cache-Control' => 'public, max-age=3600' );
    $c->res->body( Encode::encode( 'UTF-8', join "\n", @out ) );
}

sub _xml {
    my $s = shift;
    $s =~ s/&/&amp;/g; $s =~ s/</&lt;/g; $s =~ s/>/&gt;/g;
    return $s;
}

__PACKAGE__->meta->make_immutable;

1;
