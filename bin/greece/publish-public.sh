#!/bin/sh
# Copies the parts of this deployment that run inside FixMyStreet and are served to visitors
# (the Greece cobrand: Perl modules, templates, JavaScript/CSS and the Greek translation) to the
# `greece` branch of the public fork, which is based on the FixMyStreet release the site runs.
# FixMyStreet is under the GNU AGPL v3, so the site offers this source to its users (footer link).
# Data, data scripts, server configuration, separate services and secrets are not copied.
#
# Usage: bin/greece/publish-public.sh <worktree of the public fork, on branch greece> "<message>"
# Then review `git -C <worktree> show --stat` and push the branch.
set -eu

src=$(cd "$(dirname "$0")/../.." && pwd)
dst=${1:?worktree of the public fork, on branch greece}
msg=${2:?commit message}

PATHS="
perllib/FixMyStreet/Cobrand/Greece.pm
perllib/FixMyStreet/Map/Greece.pm
perllib/FixMyStreet/App/Controller/GreeceVote.pm
perllib/FixMyStreet/App/Controller/GreecePhoto.pm
perllib/FixMyStreet/App/Controller/GreeceAuth.pm
perllib/FixMyStreet/App/Controller/GreeceSocial.pm
perllib/FixMyStreet/App/Controller/GreeceNearby.pm
perllib/FixMyStreet/App/Controller/GreeceReportRef.pm
perllib/FixMyStreet/App/Controller/GreeceVideo.pm
perllib/FixMyStreet/App/Controller/GreeceOTP.pm
perllib/FixMyStreet/App/Controller/GreecePassword.pm
perllib/FixMyStreet/App/Controller/GreeceTwoFactor.pm
perllib/FixMyStreet/App/Controller/GreeceAccount.pm
perllib/FixMyStreet/App/Controller/GreeceApprove.pm
perllib/FixMyStreet/App/Controller/GreeceEdit.pm
perllib/FixMyStreet/App/Controller/GreecePrivacy.pm
docker/greece/overlay
docker/greece/video
perllib/FixMyStreet/PhotoStorage/Greece.pm
perllib/Utils.pm
perllib/FixMyStreet/Script/UpdateAllReports.pm
data/greece/votes.sql
bin/greece/send-digest
data/greece/contacts/digest.sql
templates/web/greece
templates/email/greece
web/cobrands/greece
locale/el_GR.UTF-8/LC_MESSAGES/FixMyStreet.po
"

[ "$(git -C "$dst" rev-parse --abbrev-ref HEAD)" = greece ] || { echo "$dst is not on branch greece" >&2; exit 1; }
[ -z "$(git -C "$dst" status --porcelain)" ] || { echo "$dst has uncommitted changes" >&2; exit 1; }

for p in $PATHS; do
    rm -rf "${dst:?}/$p"
    mkdir -p "$(dirname "$dst/$p")"
    # Only files git tracks here: no compiled templates (.ttc) or other local files.
    git -C "$src" ls-files -z -- "$p" | (cd "$src" && xargs -0 -r cp --parents -t "$dst")
done

# The admin's runbook (procedures, server paths, who to ask) is not part of what visitors are served.
rm -f "$dst/templates/web/greece/admin/greece_handbook.html"

# Nothing private may leave: stop on addresses, keys or hosts of the deployment.
if grep -rIl -E 'BEGIN [A-Z ]*PRIVATE KEY|@fixmystreets\.gr|uns\.gr|vitaldata|kouak|10\.0\.201\.|192\.168\.' \
        $(for p in $PATHS; do echo "$dst/$p"; done) 2>/dev/null; then
    echo "private details found in the files above; nothing committed" >&2
    exit 1
fi

# -f: the release ignores web/cobrands/*/*.css (compiled SCSS); the Greece CSS is plain CSS.
git -C "$dst" add -A -f -- $PATHS
if git -C "$dst" diff --cached --quiet; then
    echo "no changes"
    exit 0
fi
# The public commits carry the project's name, not a person's (owner, 2026-10-28); the address is not a
# GitHub account, so the commits link to no profile.
git -C "$dst" -c user.name="VitalData Services" -c user.email="noreply@fixmystreets.gr" commit -q -m "$msg"
git -C "$dst" show --stat --format='%h %s' HEAD | tail -n +1
