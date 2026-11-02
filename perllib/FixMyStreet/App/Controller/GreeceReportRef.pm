package FixMyStreet::App::Controller::GreeceReportRef;
use Moose;
use namespace::autoclean;
use JSON::MaybeXS ();
BEGIN { extends 'Catalyst::Controller'; }

=head1 NAME

FixMyStreet::App::Controller::GreeceReportRef - a report's page at its number (Greece cobrand)

=head1 DESCRIPTION

A report's address is its number, /report/20261026-03 (FixMyStreet::Cobrand::Greece greece_ref).
FixMyStreet's /report/<id> takes digits only (and sends «20261026-03» to /report/20261026), so
nginx rewrites /report/<YYYYMMDD-NN> to /greece/report-ref/<YYYYMMDD-NN>; this finds the id and
runs FixMyStreet's report page for it, at the same address. The older DDMMYYYY-N numbers redirect
to the new address.

=cut

sub report_ref : Path('/greece/report-ref') : Args(1) {
    my ( $self, $c, $ref ) = @_;
    $c->detach('/page_error_404_not_found', []) unless $c->cobrand->moniker eq 'greece';
    my $id = FixMyStreet::DB::Result::Problem::greece_id_for_ref($ref // '');
    $c->detach('/page_error_404_not_found', []) unless $id;
    unless ($ref =~ /^20\d{6}-\d+$/) {
        my $problem = $c->cobrand->problems->find({ id => $id });
        $c->detach('/page_error_404_not_found', []) unless $problem;
        $c->res->redirect($c->uri_for($problem->url), 301);
        $c->detach;
    }
    $c->go('/report/display', [ $id ], []);
}

=head2 points

/greece/report-points: GeoJSON of the visible, public reports (point, number, title) for the home page map
(web/cobrands/greece/minimap.js), which draws them as clusters. Only what the report pages already show to
anyone; cached for a minute. Lives here because each controller is its own file mount in the container.

=cut

sub points : Path('/greece/report-points') : Args(0) {
    my ( $self, $c ) = @_;
    $c->detach('/page_error_404_not_found', []) unless $c->cobrand->moniker eq 'greece';
    my @features;
    my $rs = $c->cobrand->problems->search(
        { non_public => 0, state => [ FixMyStreet::DB::Result::Problem->visible_states ] },
        { order_by => { '-desc' => 'confirmed' }, rows => 5000 });
    while ( my $p = $rs->next ) {
        next unless defined $p->latitude && defined $p->longitude;
        push @features, {
            type => 'Feature',
            geometry => { type => 'Point', coordinates => [ $p->longitude + 0, $p->latitude + 0 ] },
            properties => { ref => $p->greece_ref, title => $p->title },
        };
    }
    $c->res->content_type('application/json; charset=utf-8');
    $c->res->header( 'Cache-Control' => 'public, max-age=60' );
    $c->res->body( JSON::MaybeXS->new( utf8 => 1 )->encode({ type => 'FeatureCollection', features => \@features }) );
}


__PACKAGE__->meta->make_immutable;

1;
