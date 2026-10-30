#!/usr/bin/env bash
# Report writer's pull script. Copies each teammate's work into
# ~/cptc-work/incoming/<name>/ on this machine.
# Usage:
#   ./pull.sh --setup   once at kickoff: asks for each teammate's name, login and IP
#   ./pull.sh           pull every teammate
#   ./pull.sh <name>    pull one teammate
# The teammate list is ~/cptc-work/teammates.txt, one line per teammate:
#   name<TAB>login<TAB>IP
# It holds engagement IPs, so it lives in the working copy (no .git), never the repo.
set -euo pipefail
# The checks below use ranges like [a-z]. In some locales (e.g. Latin-1)
# [a-z] also matches accented letters, so pin the plain C locale, where it
# means exactly the 26 ASCII letters.
export LC_ALL=C

WORKDIR="$HOME/cptc-work"
CONFIG="$WORKDIR/teammates.txt"
# A key used only for pulling, so setup never changes or relies on your own
# default key. It has no passphrase, so pulls run without typing anything.
# Delete it (and its .pub) after the event.
KEY="$HOME/.ssh/cptc_ed25519"

# The name becomes the folder incoming/<name>/, so only lowercase letters,
# digits and "-" are allowed, starting with a letter or digit. That rules out
# "/", "..", spaces and a leading "-", so a name can't point outside incoming/.
# It is the same alphabet the notebook uses for field-notes/<name>/.
NAME_RULE='^[a-z0-9][a-z0-9-]*$'
# A Linux login (the useradd default). No leading "-", so ssh can't read it as an option.
LOGIN_RULE='^[a-z_][a-z0-9_-]*$'
# A dotted IPv4 address: the boxes share one IPv4 subnet. It doesn't check
# each part is 255 or less; ssh reports a wrong address when it connects.
IP_RULE='^[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}$'
COUNT_RULE='^[1-9][0-9]*$'

fail() {
  echo "pull: $1" >&2
  exit 1
}

# Print a question, then read one answer into the variable named by $2.
# The question goes to stdout with printf, not `read -p`: read -p shows
# nothing when the answers come from a file or a pipe.
ask() {
  printf '%s' "$1"
  # Plain `read -r` also trims spaces around the answer, so a stray space
  # typed after a name isn't kept.
  read -r "$2" || fail "setup stopped: no answer to \"$1\""
}

# Stop unless $1 matches the rule $2. $3 names the field in the message.
check_value() {
  [[ "$1" =~ $2 ]] || fail "$3 \"$1\" is not allowed. $4"
}

# A rerun of --setup must never silently replace the kickoff list, so show
# what is there and replace it only on a typed "yes". Succeeds only on "yes".
confirm_replace() {
  echo "A teammate list already exists: $CONFIG"
  cat "$CONFIG"
  ask "Replace it? Type yes to replace it, or anything else to keep it and redo the key step: " reply
  [ "$reply" = "yes" ]
}

# A rerun usually means one teammate's key copy failed (their ssh server
# wasn't up yet). Keeping the list means nobody retypes the whole team: it is
# checked like a pull checks it, then only the key steps run again.
run_setup() {
  [ -d "$WORKDIR" ] || fail "no working copy at $WORKDIR. Create it first with make-workcopy.sh."
  if [ -e "$CONFIG" ] && ! confirm_replace; then
    check_list
    echo "Kept $CONFIG"
  else
    ask_for_teammates
  fi
  make_key
  copy_key_to_teammates
}

# Ask for every teammate, then write the whole list at once. Nothing is
# written until every answer has passed its check.
ask_for_teammates() {
  ask "How many teammates will you pull from? " count
  check_value "$count" "$COUNT_RULE" "Teammate count" "Type a whole number, 1 or more."

  local lines="" names=" " i name login ip
  for ((i = 1; i <= count; i++)); do
    ask "Teammate $i name: " name
    check_value "$name" "$NAME_RULE" "Name" "Use lowercase letters, digits and -, starting with a letter or digit."
    # Two teammates with one name would share one incoming/<name>/ folder.
    case "$names" in
      *" $name "*) fail "name \"$name\" is already used by another teammate." ;;
    esac
    names="$names$name "
    ask "Teammate $i login: " login
    check_value "$login" "$LOGIN_RULE" "Login" "Use the Linux login, e.g. kali."
    ask "Teammate $i IP: " ip
    check_value "$ip" "$IP_RULE" "IP" "Use a dotted IPv4 address, e.g. 10.0.0.5."
    lines="$lines$name"$'\t'"$login"$'\t'"$ip"$'\n'
  done

  # Write a new file beside the old one, then rename it over the old one.
  # The rename is one step, so a crash or Ctrl-C leaves the old list or the
  # new one, never half of each. mktemp makes the file readable only by you.
  local tmp
  tmp="$(mktemp "$WORKDIR/.teammates.XXXXXX")"
  printf '%s' "$lines" > "$tmp"
  mv -f "$tmp" "$CONFIG"
  echo "Saved $count teammate(s) to $CONFIG"
}

# Create the pull key only if it isn't there yet, so a rerun keeps the key
# teammates have already accepted.
make_key() {
  if [ -f "$KEY" ] && [ -f "$KEY.pub" ]; then
    echo "Using the existing pull key $KEY"
    return
  fi
  # Half a key can't be used, and ssh-keygen would stop to ask about
  # overwriting it, so leave it for a person to look at. -L also counts a
  # broken symlink, which -e misses: ssh-keygen would write through it.
  if [ -e "$KEY" ] || [ -L "$KEY" ] || [ -e "$KEY.pub" ] || [ -L "$KEY.pub" ]; then
    fail "the pull key is incomplete or a broken link ($KEY, $KEY.pub). Delete both and run setup again."
  fi
  echo "Creating the pull key $KEY"
  # ~/.ssh must exist for ssh-keygen to write there; 700 is the mode ssh expects.
  mkdir -p -m 700 "$HOME/.ssh"
  # -N "" means no passphrase; -q keeps its output short.
  ssh-keygen -q -t ed25519 -N "" -C cptc-pull -f "$KEY" || fail "ssh-keygen could not create $KEY."
}

# Add the pull key to each teammate's box. Each teammate's password is typed
# here once; after that, pulls log in with the key.
# A failure doesn't stop the others, so one box that isn't ready yet doesn't
# make you retype every password. Setup still exits nonzero and names it.
copy_key_to_teammates() {
  local name login ip failed=""
  # The list is read on file descriptor 3, so ssh-copy-id keeps the keyboard
  # for the password and can't swallow the rest. "|| [ -n ... ]": as in check_list.
  while IFS=$'\t' read -r -u 3 name login ip || [ -n "$name" ]; do
    echo "Copying the pull key to $name ($login@$ip). Type $name's password when asked."
    if ! ssh-copy-id -i "$KEY.pub" "$login@$ip"; then
      echo "pull: could not copy the key to $name ($login@$ip)." >&2
      failed="$failed $name"
    fi
  done 3< "$CONFIG"
  if [ -n "$failed" ]; then
    fail "the key is not on:$failed. Check their ssh server is running and the password is right, then run setup again and keep the list."
  fi
  echo "Setup done. Pulls can now log in without a password."
}

# Every pull reads the list, so without it there is nothing to do yet.
# $0 is the path this script was started with, so the hint can be pasted as is.
require_config() {
  [ -f "$CONFIG" ] || fail "no teammate list at $CONFIG. Run setup first: $0 --setup"
}

# The list may have been edited by hand since setup, so check every line
# with setup's rules before pulling anyone. A bad name could otherwise
# point the copy outside incoming/, and a repeated name would make two
# teammates overwrite one incoming/<name>/ folder.
check_list() {
  local name login ip line=0 names=" "
  # "|| [ -n "$name" ]" keeps a last line that has no newline (an edit by
  # hand): read returns false for it but has still filled in the fields.
  while IFS=$'\t' read -r -u 3 name login ip || [ -n "$name" ]; do
    line=$((line + 1))
    check_value "$name" "$NAME_RULE" "$CONFIG line $line: name" "Fix it or run $0 --setup again."
    case "$names" in
      *" $name "*) fail "$CONFIG line $line: name \"$name\" is already used by another teammate. Fix it or run $0 --setup again." ;;
    esac
    names="$names$name "
    check_value "$login" "$LOGIN_RULE" "$CONFIG line $line: login" "Fix it or run $0 --setup again."
    check_value "$ip" "$IP_RULE" "$CONFIG line $line: IP" "Fix it or run $0 --setup again."
  done 3< "$CONFIG"
}

# Copy one teammate's four shared folders into incoming/<name>/ in one rsync
# call, so one ssh connection per teammate.
#   --include ... --exclude '*'  only findings/, evidence/, field-notes/ and
#       tracker/ (the leading / anchors each to the top of cptc-work/). Their
#       notes/, build/ and anything else are never copied.
#   --delete            a file the teammate deleted is deleted here too.
#   --delete-excluded   also removes anything else in incoming/<name>/ (e.g.
#       left from an unpacked zip), so it holds only those four folders.
#   -e ssh -i KEY       log in with the pull key from setup. IdentitiesOnly
#       stops ssh trying unrelated keys offered by your agent. BatchMode
#       makes ssh fail instead of asking for a password, so a pull never
#       waits at a password prompt.
# The source "cptc-work/" is relative to the teammate's home folder. Nothing
# is written on the teammate's box: it is only the source.
pull_one() {
  local name="$1" login="$2" ip="$3"
  local dest="$WORKDIR/incoming/$name"
  echo "Pulling $name ($login@$ip) into $dest/"
  # rsync would write through a symlinked folder to wherever it points.
  if [ -L "$dest" ]; then
    echo "pull: $dest is a symlink, so $name was not pulled." >&2
    return 1
  fi
  # Called inside "if", where set -e is off, so a failure must return itself.
  mkdir -p "$dest" || return 1
  rsync -a --delete --delete-excluded \
    -e "ssh -i '$KEY' -o IdentitiesOnly=yes -o BatchMode=yes" \
    --include='/findings/***' --include='/evidence/***' \
    --include='/field-notes/***' --include='/tracker/***' --exclude='*' \
    "$login@$ip:cptc-work/" "$dest/"
}

# Pull every teammate, or only the one named. A failed teammate doesn't stop
# the rest: fresh copies of the others are still worth having. The run still
# exits nonzero and names who failed, so a partial pull is never silent.
run_pull() {
  local wanted="$1" name login ip found="" failed="" pulled=0
  while IFS=$'\t' read -r -u 3 name login ip || [ -n "$name" ]; do
    if [ -n "$wanted" ] && [ "$name" != "$wanted" ]; then
      continue
    fi
    found=yes
    if pull_one "$name" "$login" "$ip"; then
      pulled=$((pulled + 1))
    else
      echo "pull: $name failed." >&2
      failed="$failed $name"
    fi
  done 3< "$CONFIG"
  if [ -z "$found" ] && [ -z "$wanted" ]; then
    fail "$CONFIG lists no teammates. Run setup again: $0 --setup"
  fi
  [ -n "$found" ] || fail "no teammate named \"$wanted\" in $CONFIG."
  echo "Pulled $pulled teammate(s)."
  [ -z "$failed" ] || fail "not pulled:$failed. Check their box is on and ssh is running, then pull again."
}

main() {
  [ $# -le 1 ] || fail "too many arguments. Use: $0 [--setup | <name>]"
  # An empty name (e.g. from an unset variable) must not mean "everyone".
  [ $# -eq 0 ] || [ -n "$1" ] || fail "the name is empty. Use: $0 [--setup | <name>]"
  if [ "${1:-}" = "--setup" ]; then
    run_setup
    return
  fi
  require_config
  [ -f "$KEY" ] || fail "no pull key at $KEY. Run setup first: $0 --setup"
  # Same reason as the per-teammate check: never write through a link.
  [ ! -L "$WORKDIR/incoming" ] || fail "$WORKDIR/incoming is a symlink. Nothing was pulled."
  check_list
  run_pull "${1:-}"
}

main "$@"
