#!/usr/bin/env bash
# Make your competition working copy, ~/cptc-work, once at kickoff.
# Usage: ./make-workcopy.sh <yourname> <source>
#   <source> is the team repo: a clone already on this box (a folder path)
#   or a Git URL. Either way it is cloned fresh into ~/cptc-work.
# Then it removes ~/cptc-work/.git, so nothing in the copy can be committed,
# and creates:
#   field-notes/<yourname>/  incoming/  tracker/ (a copy of templates/tracker/)
#   exclude.txt (empty)      .cptc-name (your name, read by logged-shell.sh)
# It refuses if ~/cptc-work already exists, so it never overwrites event work.
set -euo pipefail
# The name check uses [a-z]. In some locales (e.g. Latin-1) [a-z] also
# matches accented letters, so pin the plain C locale.
export LC_ALL=C

WORKDIR="$HOME/cptc-work"
# Same rule as pull.sh: the name becomes field-notes/<name>/ and the
# report writer's incoming/<name>/, so only lowercase letters, digits and
# "-", starting with a letter or digit. That rules out "/", ".." and spaces.
NAME_RULE='^[a-z0-9][a-z0-9-]*$'

fail() {
  echo "make-workcopy: $1" >&2
  exit 1
}

# After the clone, a failed step leaves a half-made copy, and a rerun
# would refuse it. Say how to start over.
fail_partial() {
  fail "$1 $WORKDIR is incomplete: delete it, then run this again."
}

check_arguments() {
  [ $# -eq 2 ] || fail "Use: $0 <yourname> <clone-folder-or-git-url>"
  [[ "$1" =~ $NAME_RULE ]] || fail "name \"$1\" is not allowed. Use lowercase letters, digits and -, starting with a letter or digit."
  [ -n "$2" ] || fail "the source is empty. Give the team repo's folder or Git URL."
  # -L also catches a broken symlink, which -e misses; git would follow it.
  if [ -e "$WORKDIR" ] || [ -L "$WORKDIR" ]; then
    fail "$WORKDIR already exists, so nothing was changed."
  fi
}

main() {
  check_arguments "$@"
  local name="$1" source="$2"

  # "--" stops git reading a source that starts with "-" as an option.
  git clone -- "$source" "$WORKDIR" || fail "git clone of $source failed."
  # Only the clone's own .git goes; everything else is the team's files.
  rm -rf -- "$WORKDIR/.git" || fail_partial "could not remove $WORKDIR/.git."

  # Check before adding anything to the copy, so a wrong source stops here.
  # A repo can hold symlinks, and a write or copy through one could land
  # outside ~/cptc-work, so none of the paths used below may be a link.
  local path
  for path in templates templates/tracker field-notes "field-notes/$name" incoming; do
    [ ! -L "$WORKDIR/$path" ] || fail_partial "$WORKDIR/$path is a symlink in the source."
  done
  # These three are made fresh, so one already there would be overwritten.
  # -L also catches a broken symlink, which -e misses.
  for path in tracker exclude.txt .cptc-name; do
    if [ -e "$WORKDIR/$path" ] || [ -L "$WORKDIR/$path" ]; then
      fail_partial "$WORKDIR/$path already came with the source."
    fi
  done
  [ -d "$WORKDIR/templates/tracker" ] || fail_partial "$source has no templates/tracker/: is it the team repo?"

  mkdir -p "$WORKDIR/field-notes/$name" "$WORKDIR/incoming" || fail_partial "could not create field-notes/$name/ and incoming/."
  # tracker/ doesn't exist yet, so cp -R creates it as a copy (not tracker/tracker/).
  cp -R "$WORKDIR/templates/tracker" "$WORKDIR/tracker" || fail_partial "could not copy templates/tracker/ to tracker/."
  : > "$WORKDIR/exclude.txt" || fail_partial "could not create exclude.txt."
  printf '%s\n' "$name" > "$WORKDIR/.cptc-name" || fail_partial "could not save your name in .cptc-name."

  echo "Made $WORKDIR for $name."
  echo "Work only in $WORKDIR from now on, and open every terminal there."
}

main "$@"
