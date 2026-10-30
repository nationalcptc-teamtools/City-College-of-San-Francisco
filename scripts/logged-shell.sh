#!/usr/bin/env bash
# Start a bash session that writes two logs:
#   1. <name>_<UTC timestamp>.log       full transcript (input and output), via util-linux `script`
#   2. <name>_<UTC timestamp>.cmds.log  one line per command: time, exit code, directory, command
# The second log is the quick index for incident reports and reproduction steps.
# Usage: ./logged-shell.sh [name]   -> logs go to $LOGDIR (default ~/cptc-logs)
set -euo pipefail

# The session name: the argument if given, else the one make-workcopy.sh
# saved in ~/cptc-work/.cptc-name, else your login. The login is a last
# resort with a warning: every event box may log in as kali, so logs named
# after it can't be told apart. Logging still starts, because an unlogged
# terminal can't be redone and a wrongly named log can be renamed.
# A typed name must pass the same rule: one with "/" or ".." would put the
# logs outside LOGDIR, so a bad one stops the script before any log exists.
pick_name() {
  # Same rule as make-workcopy.sh, in the C locale: elsewhere [a-z] can match accented
  # letters. pick_name runs inside $(...) (line 48), so this never reaches your shell.
  local LC_ALL=C rule='^[a-z0-9][a-z0-9-]*$'
  if [ -n "$1" ]; then
    if [[ "$1" =~ $rule ]]; then
      printf '%s\n' "$1"   # printf, not echo: echo reads some words as its own options
      return
    fi
    echo "logged-shell: name \"$1\" is not allowed. Use lowercase letters, digits and -, starting with a letter or digit." >&2
    return 1
  fi
  local file="$HOME/cptc-work/.cptc-name" saved="" extra=""
  # -r: an unreadable file gets the warning below, not an error from bash.
  if [ -f "$file" ] && [ -r "$file" ]; then
    {
      IFS= read -r saved   # a last line with no newline still fills saved
      # One line only: anything after it, even an empty line, makes it invalid.
      if IFS= read -r extra || [ -n "$extra" ]; then
        saved=""
      fi
    } < "$file"
  fi
  if [[ "$saved" =~ $rule ]]; then
    printf '%s\n' "$saved"
    return
  fi
  echo "logged-shell: no valid name in $file, so these logs are named after your login ($(whoami)). Next time: $0 <yourname>" >&2
  whoami
}

LOGDIR="${LOGDIR:-$HOME/cptc-logs}"
name="$(pick_name "${1:-}")" || exit 1   # pick_name has already said why
ts="$(date -u +%Y%m%dT%H%M%SZ)"
log="$LOGDIR/${name}_${ts}.log"
cmdlog="$LOGDIR/${name}_${ts}.cmds.log"
mkdir -p "$LOGDIR"

rc="$(mktemp)"
# Unquoted heredoc on purpose: $cmdlog is filled in now. Every \$ stays literal for the new shell.
cat >"$rc" <<EOF
[ -f ~/.bashrc ] && . ~/.bashrc
CPTC_CMDLOG='$cmdlog'
HISTTIMEFORMAT='%F %T '
HISTCONTROL=   # log every command, including repeats and ones typed with a leading space
# After each command: save the exit code first, then append one line to the command log.
# A line is written only when the history number changes, so the first prompt and
# pressing Enter on an empty line add nothing.
__cptc_log() {
  local code=\$? line num cmd
  line="\$(history 1)"
  num="\$(sed -E 's/^ *([0-9]+).*/\\1/' <<<"\$line")"
  if [ -n "\${__cptc_ready:-}" ] && [ "\$num" != "\$__cptc_last" ]; then
    cmd="\$(sed -E 's/^ *[0-9]+ +[0-9-]+ [0-9:]+ +//' <<<"\$line")"
    printf '%s (exit %s) [%s] %s\\n' "\$(date '+%F %T %Z')" "\$code" "\$PWD" "\$cmd" >> "\$CPTC_CMDLOG"
  fi
  __cptc_last="\$num"
  __cptc_ready=1
}
PROMPT_COMMAND=__cptc_log
PS1='[\D{%F %T %Z}] \u@\h:\w\\$ '
EOF

echo "Logging to $log"
echo "Command index: $cmdlog  (type 'exit' to stop)"
# util-linux script: -q quiet, -f flush after each write so the log is current.
script -q -f -c "bash --rcfile '$rc'" "$log"
rm -f "$rc"
echo "Session saved: $log"
echo "Command index: $cmdlog"
