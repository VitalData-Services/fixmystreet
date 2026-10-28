package FixMyStreet::App::Controller::GreeceHandbook;
use Moose;
use namespace::autoclean;
BEGIN { extends 'Catalyst::Controller'; }

=head1 NAME

FixMyStreet::App::Controller::GreeceHandbook - what the admin does, and when, in each case (Greece cobrand)

=head1 DESCRIPTION

  GET /admin/greece/handbook

A page for the superusers: the routine, the data-subject requests and their deadlines, the privacy flag, a
breach, a request from an authority, with the steps and reply texts to copy (templates/web/greece/admin/
greece_handbook.html). Static text; superusers only, behind the second sign-in step like the rest of /admin.

=cut

sub handbook : Path('/admin/greece/handbook') : Args(0) {
    my ( $self, $c ) = @_;
    $c->detach('/page_error_404_not_found', []) unless $c->cobrand->moniker eq 'greece';
    return $c->res->redirect('/auth?r=/admin/greece/handbook') unless $c->user_exists;
    $c->detach('/page_error_403_access_denied', ['']) unless $c->user->is_superuser;
    $c->stash->{template} = 'admin/greece_handbook.html';
}

__PACKAGE__->meta->make_immutable;

1;
