package FixMyStreet::App::Controller::GreeceRequests;
use Moose;
use namespace::autoclean;
use utf8;
BEGIN { extends 'Catalyst::Controller'; }

=head1 NAME

FixMyStreet::App::Controller::GreeceRequests - the request desk: rights requests of citizens and their deadlines

=head1 DESCRIPTION

  GET  /admin/greece/requests          the list, open requests first, nearest deadline first
  POST /admin/greece/requests          a new request (kind, email, optional report number and date received)
  GET  /admin/greece/requests/<id>     one request: the facts, the buttons and the reply text
  POST /admin/greece/requests/<id>     action = status | note | extend

A request is one row of C<greece_request> (data/greece/requests.sql). Its deadline is one month from the day it
was received; one extension, to three months, needs a written reason (GDPR Art. 12(3)). The answered
requests are deleted three years after the answer (bin/greece/retention). bin/greece/requests-reminder emails
the contact address the open ones that are due in a week or already late.

Superusers only, CSRF-checked, behind the second sign-in step like /admin/greece/approve.

=cut

our %KINDS = (
    access  => 'Πρόσβαση / αντίγραφο',
    erase   => 'Διαγραφή',
    rectify => 'Διόρθωση',
    object  => 'Ένσταση / περιορισμός',
    recall  => 'Ανάκληση από δήμο ή αστυνομία',
    privacy => 'Απόκρυψη για ιδιωτικότητα',
    notice  => 'Αναφορά περιεχομένου',
);
our %STATUSES = (
    new      => 'Νέο',
    waiting  => 'Περιμένει τον πολίτη',
    ready    => 'Έτοιμο για απάντηση',
    answered => 'Απαντήθηκε',
);
my $TODAY = "(now() at time zone 'Europe/Athens')::date";

sub _gate {
    my ( $self, $c ) = @_;
    $c->detach('/page_error_404_not_found', []) unless $c->cobrand->moniker eq 'greece';
    unless ($c->user_exists) {
        $c->res->redirect('/auth?r=' . $c->req->uri->path);
        $c->detach;
    }
    $c->detach('/page_error_403_access_denied', ['']) unless $c->user->is_superuser;
}

sub _dbh { FixMyStreet::DB->schema->storage->dbh }

sub _trim {
    my $s = shift // '';
    $s =~ s/^\s+|\s+$//g;
    return $s;
}

# The state of a request as a line: answered, late, soon or comfortable.
sub _badge {
    my ($r) = @_;
    return '✓ απαντήθηκε' . ($r->{answered} ? " $r->{answered}" : '') if $r->{status} eq 'answered';
    my $d = $r->{days_left};
    return '🔴 σε καθυστέρηση ' . (-$d) . ($d == -1 ? ' ημέρα' : ' ημέρες') if $d < 0;
    return '🟠 λήγει σήμερα' if $d == 0;
    return '🟠 σε ' . $d . ($d == 1 ? ' ημέρα' : ' ημέρες') if $d <= 7;
    return '🟢 σε ' . $d . ' ημέρες';
}

sub list : Path('/admin/greece/requests') : Args(0) {
    my ( $self, $c ) = @_;
    $self->_gate($c);
    my $dbh = _dbh();

    if ($c->req->method eq 'POST') {
        $c->forward('/auth/check_csrf_token');
        my $kind = _trim($c->get_param('kind'));
        my $email = lc _trim($c->get_param('email'));
        my $ref = _trim($c->get_param('report_ref'));
        my $note = _trim($c->get_param('note'));
        my $received = _trim($c->get_param('received'));
        $received = undef unless $received =~ /^\d{4}-\d{2}-\d{2}$/;
        my $error;
        $error = 'Διάλεξε είδος αιτήματος.' unless $KINDS{$kind};
        $error ||= 'Γράψε ένα έγκυρο email.' unless $email =~ /^[^@\s]+@[^@\s]+\.[^@\s]+$/ && length $email <= 200;
        $error ||= 'Ο αριθμός αναφοράς είναι πολύ μεγάλος.' if length $ref > 40;
        $error ||= 'Η σημείωση είναι πολύ μεγάλη.' if length $note > 2000;
        if (!$error) {
            my ($id) = $dbh->selectrow_array(
                "INSERT INTO greece_request (kind, email, received, due, report_ref, note, handled_by)
                 VALUES (?, ?, COALESCE(?::date, $TODAY), COALESCE(?::date, $TODAY) + interval '1 month', ?, ?, ?)
                 RETURNING id", undef, $kind, $email, $received, $received, $ref || undef, $note || undef, $c->user->id);
            $c->log->info("greece request $id: created by user " . $c->user->id . " ($kind)");
            return $c->res->redirect($c->uri_for('/admin/greece/requests', $id));
        }
        $c->stash->{error} = $error;
        $c->stash->{form} = { kind => $kind, email => $email, report_ref => $ref, note => $note, received => $received };
    }

    my $rows = $dbh->selectall_arrayref(
        "SELECT id, kind, email, to_char(received, 'DD/MM/YYYY') AS received, to_char(due, 'DD/MM/YYYY') AS due,
                (due - $TODAY) AS days_left, status, report_ref, to_char(answered, 'DD/MM/YYYY') AS answered
           FROM greece_request
          ORDER BY (status = 'answered'), CASE WHEN status = 'answered' THEN NULL ELSE due END, (CASE WHEN status = 'answered' THEN answered END) DESC NULLS LAST, id DESC
          LIMIT 200", { Slice => {} });
    for my $r (@$rows) {
        $r->{kind_label} = $KINDS{ $r->{kind} } // $r->{kind};
        $r->{status_label} = $STATUSES{ $r->{status} } // $r->{status};
        $r->{badge} = _badge($r);
    }
    $c->stash->{requests} = $rows;
    $c->stash->{kinds} = [ map { { key => $_, label => $KINDS{$_} } } qw(access erase rectify object recall privacy notice) ];
    $c->stash->{csrf_token} = $c->forward('/auth/get_csrf_token');
    $c->stash->{template} = 'admin/greece_requests.html';
}

sub one : Path('/admin/greece/requests') : Args(1) {
    my ( $self, $c, $id ) = @_;
    $self->_gate($c);
    $c->detach('/page_error_404_not_found', []) unless $id =~ /^\d+$/;
    my $dbh = _dbh();

    if ($c->req->method eq 'POST') {
        $c->forward('/auth/check_csrf_token');
        my $action = $c->get_param('action') // '';
        my $uid = $c->user->id;
        if ($action eq 'status') {
            my $status = $c->get_param('status') // '';
            $c->detach('/page_error_400_bad_request', ['status']) unless $STATUSES{$status};
            $dbh->do("UPDATE greece_request SET status = ?, answered = CASE WHEN ? = 'answered' THEN COALESCE(answered, $TODAY) ELSE NULL END,
                      handled_by = ?, updated = now() WHERE id = ?", undef, $status, $status, $uid, $id);
        } elsif ($action eq 'note') {
            my $note = _trim($c->get_param('note'));
            my $ref = _trim($c->get_param('report_ref'));
            $c->detach('/page_error_400_bad_request', ['length']) if length $note > 2000 || length $ref > 40;
            $dbh->do('UPDATE greece_request SET note = ?, report_ref = ?, handled_by = ?, updated = now() WHERE id = ?',
                undef, $note || undef, $ref || undef, $uid, $id);
        } elsif ($action eq 'extend') {
            my $reason = _trim($c->get_param('reason'));
            if ($reason ne '' && length $reason <= 500) {
                # Once, to three months from the day it was received; the citizen is told within the first month.
                $dbh->do("UPDATE greece_request SET due = received + interval '3 months', extended_reason = ?, handled_by = ?, updated = now()
                          WHERE id = ? AND extended_reason IS NULL", undef, $reason, $uid, $id);
            }
        }
        $c->log->info("greece request $id: $action by user $uid");
        return $c->res->redirect($c->uri_for('/admin/greece/requests', $id));
    }

    my $r = $dbh->selectrow_hashref(
        "SELECT id, kind, email, to_char(received, 'DD/MM/YYYY') AS received, to_char(due, 'DD/MM/YYYY') AS due,
                (due - $TODAY) AS days_left, status, report_ref, note, extended_reason, to_char(answered, 'DD/MM/YYYY') AS answered
           FROM greece_request WHERE id = ?", undef, $id);
    $c->detach('/page_error_404_not_found', []) unless $r;
    $r->{kind_label} = $KINDS{ $r->{kind} } // $r->{kind};
    $r->{status_label} = $STATUSES{ $r->{status} } // $r->{status};
    $r->{badge} = _badge($r);
    $c->stash->{r} = $r;
    $c->stash->{statuses} = [ map { { key => $_, label => $STATUSES{$_} } } qw(new waiting ready answered) ];
    $c->stash->{csrf_token} = $c->forward('/auth/get_csrf_token');
    $c->stash->{template} = 'admin/greece_request.html';
}

__PACKAGE__->meta->make_immutable;

1;
