package FixMyStreet::App::Controller::GreeceApprove;
use Moose;
use namespace::autoclean;
BEGIN { extends 'Catalyst::Controller'; }

=head1 NAME

FixMyStreet::App::Controller::GreeceApprove - an admin approves the municipalities' reports (Greece cobrand)

=head1 DESCRIPTION

Reports to the municipalities leave in a batch (bin/greece/send-digest, at 09:00 and
14:00 Athens time, every day), and only once a superuser has approved them here. A report that is not approved
stays public and waits; the digest emails the contact address at each batch time while any wait.
Complaints to the police do not come here: they go at once.

  GET  /admin/greece/approve                      the waiting reports
  POST /admin/greece/approve  id=...&id=...       approves those
  POST /admin/greece/approve  all=1               approves every waiting one

Approving stores extra greece_approved = { at, by } on the report (FixMyStreet::Cobrand::Greece
greece_needs_approval). Superusers only; the second sign-in step (greece_2fa_gate) applies as everywhere.

=cut

sub approve : Path('/admin/greece/approve') : Args(0) {
    my ( $self, $c ) = @_;
    $c->detach('/page_error_404_not_found', []) unless $c->cobrand->moniker eq 'greece';
    return $c->res->redirect('/auth?r=/admin/greece/approve') unless $c->user_exists;
    $c->detach('/page_error_403_access_denied', ['']) unless $c->user->is_superuser;

    my $cobrand = $c->cobrand;
    my @waiting = grep { $cobrand->greece_needs_approval($_) } $c->model('DB::Problem')->search({
        state => [ FixMyStreet::DB::Result::Problem->open_states ],
        send_state => 'unprocessed',
        whensent => undef,
        bodies_str => { '!=' => undef },
    }, { order_by => [ 'confirmed', 'id' ] })->all;

    if ($c->req->method eq 'POST') {
        $c->forward('/auth/check_csrf_token');
        my %want = map { $_ => 1 } grep { /^\d+$/ } $c->req->param('id');
        my $all = $c->get_param('all');
        my $n = 0;
        for my $r (@waiting) {
            next unless $all || $want{ $r->id };
            $r->set_extra_metadata(greece_approved => { at => time, by => $c->user->id });
            $r->update;
            $n++;
        }
        $c->log->info("greece approve: user " . $c->user->id . " approved $n report(s)");
        return $c->res->redirect($c->uri_for('/admin', { approved => $n }) . '#gr-approve') if ($c->get_param('back') // '') eq 'summary';
        return $c->res->redirect($c->uri_for('/admin/greece/approve', { done => $n }));
    }

    $c->stash->{csrf_token} = $c->forward('/auth/get_csrf_token');
    $c->stash->{waiting} = \@waiting;
    $c->stash->{done} = $c->get_param('done');
    $c->forward('/admin/set_allowed_pages');   # the admin menu needs it, as on FixMyStreet's own admin pages
    $c->stash->{template} = 'admin/greece_approve.html';
}

=head2 users_action

  POST /admin/greece/users-action  act=disable|enable|delete & uid=...  (from the Users page)

Disable puts the user's verified email/phone in the abuse list (they cannot make reports) and signs them out
everywhere; enable takes them out of it; delete removes the personal details (FixMyStreet's «remove account»: reports
stay, anonymous) and cannot be undone. Never on yourself, on a superuser or, for delete, on staff. Superusers only.

=cut

sub users_action : Path('/admin/greece/users-action') : Args(0) {
    my ( $self, $c ) = @_;
    $c->detach('/page_error_404_not_found', []) unless $c->cobrand->moniker eq 'greece';
    return $c->res->redirect('/auth?r=/admin/users') unless $c->user_exists;
    $c->detach('/page_error_403_access_denied', ['']) unless $c->user->is_superuser;
    return $c->res->redirect($c->uri_for('/admin/users')) unless $c->req->method eq 'POST';
    $c->forward('/auth/check_csrf_token');

    my $act = $c->get_param('act') // '';
    return $c->res->redirect($c->uri_for('/admin/users')) unless $act =~ /^(disable|enable|delete)$/;
    my @ids = grep { /^\d+$/ } $c->get_param_list('uid');
    my @users = @ids ? $c->model('DB::User')->search({ id => \@ids })->all : ();
    my ($n, $skipped) = (0, 0);
    for my $u (@users) {
        my $status = $c->cobrand->greece_user_status($u);
        if ($u->id == $c->user->id || $u->is_superuser
            || ($act eq 'delete' && ($u->from_body || $status eq 'deleted'))
            || ($act ne 'delete' && $status eq 'deleted')) {
            $skipped++;
            next;
        }
        my @names;
        push @names, $u->email if $u->email_verified && $u->email;
        push @names, $u->phone if $u->phone_verified && $u->phone;
        if ($act eq 'disable') {
            unless (@names) { $skipped++; next; }
            $c->model('DB::Abuse')->find_or_create({ email => $_ }) for @names;
            $c->forward('/admin/users/user_logout_everywhere', [ $u ]);
        } elsif ($act eq 'enable') {
            $c->model('DB::Abuse')->search({ email => \@names })->delete if @names;
        } else {
            $c->forward('/admin/users/user_logout_everywhere', [ $u ]);
            $u->anonymize_account;
        }
        $c->forward('/admin/log_edit', [ $u->id, 'user', 'edit' ]);
        $n++;
    }
    $c->log->info("greece users: user " . $c->user->id . " $act $n user(s), skipped $skipped");
    my %q = ( gr_done => $act, gr_n => $n, gr_skipped => $skipped );
    my $status = $c->get_param('status');
    $q{status} = $status if $status && $status =~ /^(active|disabled|deleted|staff)$/;
    return $c->res->redirect($c->uri_for('/admin/users', \%q));
}

__PACKAGE__->meta->make_immutable;

1;
