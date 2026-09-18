#!/usr/bin/env bash
# CONNECT — open (or reuse) a persistent SSH connection to a fleet host and
# return everything needed to use it: "up host=H ctl=<socket> target=<tgt>".
#
# One connection per host, opened by the first checks of the morning; every
# later check rides the socket (11 ms warm vs 1.1 s cold). The report carries
# the socket path, so the reading agent starts the session already connected.
# Socket lives 10 minutes past last use (ControlPersist) — long enough for a
# morning's work, short enough to die on its own.
host=local; for a in "$@"; do [ "${a%%=*}" = host ] && host=${a#host=}; done
case "$host" in
  z620)  target="studi@10.0.0.10" ;;
  vultr) target="vultr" ;;
  *)     echo "down host=$host reason=unknown-host"; exit 0 ;;
esac
ctl="/tmp/orient-ssh-$host"
SOPTS="-o BatchMode=yes -o ConnectTimeout=6 -o ControlPath=$ctl"
if ssh $SOPTS -O check "$target" 2>/dev/null; then
  echo "up host=$host ctl=$ctl target=$target reused=true"
elif ssh $SOPTS -o ControlMaster=yes -o ControlPersist=600 -MNf "$target" 2>/dev/null \
  && ssh $SOPTS -O check "$target" 2>/dev/null; then
  echo "up host=$host ctl=$ctl target=$target reused=false"
else
  ssh $SOPTS -O exit "$target" >/dev/null 2>&1 || true
  echo "down host=$host target=$target"
fi
