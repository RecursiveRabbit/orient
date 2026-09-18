#!/usr/bin/env bash
# orient — Sexton's wake-up brief for the fleet.
#
# Runs on the workstation; reaches out to z620 and Vultr over ssh with
# read-only probes (stock commands, invoked plainly — if you need a modified
# behavior, fork it under a new name, never shadow the real tool).
#
# Batons are data sources on disk. Found by value with grep; read by key with
# jq/flatten. Remote batons are fetched into a temp dir that dies with the
# script — nothing persists except the report.
#
# Reports in orients/ are historical and fungible: any session may rewrite
# this script's structure, so only orients/latest.txt is trustworthy, and only
# because you can read this file and see exactly where every number came from.
# If you want data over time, build a recorder; do not scrape old reports.
#
# Edit this script freely. Nothing is special because it is old.

set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")"

STAMP=$(date -u '+%Y%m%dT%H%M%SZ')
mkdir -p orients
exec > >(tee "orients/orient-$STAMP.txt")
ln -sfn "orient-$STAMP.txt" orients/latest.txt
printf 'report: orients/orient-%s.txt\n' "$STAMP" >&2

section() { printf '\n## %s\n' "$1"; }
sub()     { printf '\n### %s\n' "$1"; }

SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=8 -o ServerAliveInterval=5 -o ServerAliveCountMax=2)
Z620=studi@10.0.0.10
VULTR=vultr

# ---------------------------------------------------------------- batons ----
# Data sources. Local paths are literal; remote ones are fetched once into a
# temp dir so every later query is a local jq call. Edit when the fleet moves.
TMPD=$(mktemp -d); trap 'rm -rf "$TMPD"' EXIT

fetch_baton() { # name host path
  ssh "${SSH_OPTS[@]}" "$2" "cat $3" >"$TMPD/$1.json" 2>/dev/null || rm -f "$TMPD/$1.json"
}
fetch_baton clawd          "$Z620"  /home/hopper/clawd/baton.json
fetch_baton neoclaw        "$Z620"  /home/hopper/clawd/projects/neoclaw/baton.json
fetch_baton neoclaw_rails  "$Z620"  /home/hopper/clawd/projects/neoclaw_rails/baton.json
fetch_baton catalog        "$Z620"  /home/hopper/clawd/town/services/parallax-catalog/baton.json
fetch_baton vultr          "$VULTR" /root/baton.json

shopt -s nullglob
BATONS=(identity.json baton.json projects/*/project.json "$TMPD"/*.json)
[ -f ~/Coding_Projects/semantic-chunking/baton.json ] && BATONS+=(~/Coding_Projects/semantic-chunking/baton.json)

baton_name() { # file -> project/resident name
  jq -r '.identity.name // .resident.name // .name // empty' "$1" 2>/dev/null | head -n1
}

# One structural pass per baton: every "port"/"*_port" field becomes a claim.
# Claims are "port<TAB>name<TAB>hosthint" in $TMPD/claims. Host hint comes
# from the entry's own host field, else the baton's surface.host, else the
# machine the baton was fetched from; empty means "any host".
: >"$TMPD/claims"
claim_file() { # file srchost
  local f=$1 srchost=$2 n
  [ -f "$f" ] || return
  n=$(baton_name "$f"); n=${n:-$(basename "$f" .json)}
  jq -r --arg n "$n" --arg srchost "$srchost" '
    def asport: if type == "number" and . == floor and . > 0 and . < 65536 then .
                elif type == "string" and test("^[0-9]+$") then tonumber
                else empty end;
    . as $root
    | [ paths(scalars) as $p
        | select(($p[-1] | type) == "string")
        | select($p[-1] == "port" or ($p[-1] | endswith("_port")))
        | (getpath($p) | asport) as $port
        | { port: $port,
            who: (if ($p | length) >= 3 and $p[0] == "active_threads" then $p[1] else $n end),
            ip: ((try getpath($p[:-1] + ["host"])) // ($root.surface.host?) // ($root.host?) // $srchost) }
      ] | unique | .[] | "\(.port)\t\(.who)\t\(.ip)"' "$f" 2>/dev/null >>"$TMPD/claims"
}
claim_file identity.json workstation
for f in baton.json projects/*/project.json; do claim_file "$f" ""; done
[ -f ~/Coding_Projects/semantic-chunking/baton.json ] && claim_file ~/Coding_Projects/semantic-chunking/baton.json ""
for rb in clawd neoclaw neoclaw_rails catalog; do claim_file "$TMPD/$rb.json" 10.0.0.10; done
claim_file "$TMPD/vultr.json" 96.30.195.214

port_owner() { # port hostlabel -> claiming project (empty if none)
  awk -F'\t' -v p="$1" -v h="$2" '
    $1 == p && ($3 == "" || $3 == h \
      || (h == "z620"  && $3 == "10.0.0.10") \
      || (h == "vultr" && $3 == "96.30.195.214")) {print $2; exit}' "$TMPD/claims"
}

# ---------------------------------------------------------------- report ----
section "Sexton orient"
printf '%-16s %s\n' generated_utc: "$STAMP"
printf '%-16s %s\n' host: "$(hostname)"
printf '%-16s %s\n' user: "$(whoami)"

section "Read first"
printf '%s\n' \
  '- Expected: z620 healthy; .home DNS answers 10.0.0.10; catalog/valley HTTP 200; valley websocket via Caddy 400; theuncannyvalley.cc HTTPS 502 (dead proxy until catalog static hosting replaces it); absurdrabbit.net has no A record.' \
  '- WARN lines are the orientation delta. No WARNs = the world matches the inherited map.' \
  '- Every number below sits next to the command that produced it in this script. Trust latest.txt only; older reports describe an older script.'

sub "workspace git"
git status --short --branch 2>/dev/null || true

section "Batons (data sources on disk)"
for f in "${BATONS[@]}"; do
  [ -f "$f" ] || continue
  n=$(baton_name "$f"); n=${n:-$(basename "$f" .json)}
  printf '%-24s %s\n' "$n" "${f/#$TMPD\//remote:}"
done
for pair in clawd neoclaw neoclaw_rails catalog vultr; do
  [ -f "$TMPD/$pair.json" ] || printf 'WARN: remote baton missing: %s\n' "$pair"
done

section "Open ports (reality, annotated from batons)"

printf '%-13s %-7s %-5s %-5s %-18s %s\n' host port proto bind process project

emit_ports() { # host proto collapse_unknown < ss -lnH[p] lines
  # One row per port, with bind scope. collapse_unknown=yes folds rows no
  # baton claims into a single NOTE (the workstation's ephemeral game/Steam
  # UDP firehose is not orientation signal).
  local host=$1 proto=$2 collapse=$3 laddr port owner
  local unknown=0
  declare -A procof=() scope=()
  while read -r _ _ _ laddr _ rest; do
    port=${laddr##*:}
    [[ $port =~ ^[0-9]+$ ]] || continue
    if [ -z "${procof[$port]+x}" ]; then
      procof[$port]=$(sed -n 's/.*users:(("\([^"]*\)".*/\1/p' <<<"$rest")
    fi
    case $laddr in
      127.* | *::1*) : ;;
      *) scope[$port]=lan ;;
    esac
  done
  for port in $(printf '%s\n' "${!procof[@]}" | grep . | sort -n); do
    owner=$(port_owner "$port" "$host")
    if [ "$collapse" = yes ] && [ -z "$owner" ]; then unknown=$((unknown+1)); continue; fi
    printf '%-13s %-7s %-5s %-5s %-18s %s\n' "$host" "$port" "$proto" "${scope[$port]:-lo}" "${procof[$port]:--}" "${owner:-unknown}"
  done
  [ "$unknown" -gt 0 ] && printf 'NOTE: %s has %d unclaimed %s listeners not shown (ephemeral desktop/game ports)\n' "$host" "$unknown" "$proto"
}

( sudo -n ss -lntHp 2>/dev/null || ss -lntHp ) | emit_ports workstation tcp no
( sudo -n ss -lnuHp 2>/dev/null || ss -lnuHp ) | emit_ports workstation udp yes
ssh "${SSH_OPTS[@]}" "$Z620"  'sudo -n ss -lntHp' 2>/dev/null | emit_ports z620 tcp no
ssh "${SSH_OPTS[@]}" "$Z620"  'sudo -n ss -lnuHp' 2>/dev/null | emit_ports z620 udp no
ssh "${SSH_OPTS[@]}" "$VULTR" 'ss -lntHp' 2>/dev/null | emit_ports vultr tcp no
ssh "${SSH_OPTS[@]}" "$VULTR" 'ss -lnuHp' 2>/dev/null | emit_ports vultr udp no

sub "firewall openings with no listener"
z620_listen=$( { ssh "${SSH_OPTS[@]}" "$Z620" 'sudo -n ss -lntHn; sudo -n ss -lnuHn' 2>/dev/null; } | awk '{print $4}' | sed 's/.*://' | grep -E '^[0-9]+$' | sort -u )
ssh "${SSH_OPTS[@]}" "$Z620" 'sudo -n ufw status' 2>/dev/null \
  | awk '/ALLOW|LIMIT/ {split($1,a,"/"); if (a[1] ~ /^[0-9]+$/) print a[1]}' | sort -u \
  | comm -23 - <(printf '%s\n' "$z620_listen") \
  | while read -r p; do printf 'WARN: z620:%s allowed by ufw but nothing listens\n' "$p"; done
vultr_listen=$( { ssh "${SSH_OPTS[@]}" "$VULTR" 'ss -lntHn; ss -lnuHn' 2>/dev/null; } | awk '{print $4}' | sed 's/.*://' | grep -E '^[0-9]+$' | sort -u )
ssh "${SSH_OPTS[@]}" "$VULTR" 'iptables -S' 2>/dev/null \
  | sed -n 's/.*--dport \([0-9]*\).* -j ACCEPT/\1/p' | sort -u \
  | comm -23 - <(printf '%s\n' "$vultr_listen") \
  | while read -r p; do printf 'WARN: vultr:%s accepted by iptables but nothing listens\n' "$p"; done

section "Names and reachability"
sub "DNS"
for name in catalog.home valley.home git.home tickets.home absurdrabbit.net theuncannyvalley.cc; do
  printf '%-24s %s\n' "$name:" "$(dig +time=3 +tries=1 "$name" A +short 2>/dev/null | paste -sd, -)"
done
for name in catalog.home valley.home git.home tickets.home; do
  printf '%-24s %s\n' "$name@z620:" "$(dig +time=3 +tries=1 @10.0.0.10 "$name" A +short 2>/dev/null | paste -sd, -)"
done
sub "HTTP"
for url in http://catalog.home/ http://valley.home/ https://theuncannyvalley.cc/; do
  printf '%-34s %s\n' "$url" "$(curl -sS -o /dev/null --max-time 12 -w '%{http_code} from %{remote_ip} in %{time_total}s' "$url" 2>&1)"
done
printf '%-34s %s\n' "http://valley.home/websocket (ws)" \
  "$(curl -sS -o /dev/null --max-time 12 -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==' -w '%{http_code}' http://valley.home/websocket 2>&1)"
sub "Vultr TCP from here"
for port in 22 80 443 2200; do
  state=$(timeout 5 bash -c "</dev/tcp/96.30.195.214/$port" >/dev/null 2>&1 && echo open || echo closed/filtered)
  printf '%-24s %s\n' "96.30.195.214:$port" "$state"
done

section "z620 / hopperworkstation"
ssh "${SSH_OPTS[@]}" "$Z620" 'sudo -n bash -s' 2>&1 <<'Z620' || printf 'WARN: z620 probe failed\n'
set -u
sub() { printf '\n### %s\n' "$1"; }
kv() { printf '%-26s %s\n' "$1:" "$2"; }

sub "host"
kv hostname "$(hostname)"; kv date_utc "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
uptime
. /etc/os-release 2>/dev/null && kv os "${PRETTY_NAME:-unknown}"
kv kernel "$(uname -sr)"
free -h | sed -n '1,2p'
df -h / /mnt/raid 2>/dev/null || df -h /
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null || true

sub "health"
failed=$(systemctl --failed --no-legend --plain 2>/dev/null)
kv failed_units "$(printf '%s\n' "$failed" | grep -c . || true)"
[ -n "$failed" ] && printf '%s\n' "$failed"
ras=$(journalctl -p err -b --no-pager 2>/dev/null | grep -Ec 'RAS:|Memory failure' || true)
kv ras_memory_error_lines "$ras"
[ "$ras" = 0 ] || echo "WARN: kernel RAS/memory failure lines this boot"
[ -n "$failed" ] && echo "WARN: failed systemd units present"

sub "key services"
for s in caddy dnsmasq docker forgejo mongod mosquitto ollama wikijs vikunja zigbee2mqtt comfyui neoclaw-rails-hub neoclaw-wg-forward; do
  kv "$s" "$(systemctl is-active "$s.service" 2>/dev/null || echo missing)"
done
hopper_uid=$(id -u hopper 2>/dev/null || echo 1000)
kv "uncanny-valley (hopper)" "$(sudo -u hopper XDG_RUNTIME_DIR=/run/user/$hopper_uid systemctl --user is-active uncanny-valley.service 2>/dev/null || echo unknown)"

sub "docker"
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' 2>/dev/null || true

sub "storage"
mdadm --detail /dev/md0 2>/dev/null | egrep 'State :|Active Devices|Failed Devices' || true
for d in /dev/sd?; do
  [ -b "$d" ] || continue
  printf '%s: %s\n' "$d" "$(smartctl -H "$d" 2>/dev/null | grep -E 'overall-health' || echo 'no SMART line')"
done

sub "dnsmasq"
kv active "$(systemctl is-active dnsmasq 2>/dev/null || true)"
grep -h '^address=' /etc/dnsmasq.d/*.conf 2>/dev/null | sort || true

sub "caddy"
kv active "$(systemctl is-active caddy 2>/dev/null || true)"
caddy validate --config /etc/caddy/Caddyfile 2>&1 | tail -2 || true

sub "updates"
printf 'upgradable_count: '; apt list --upgradable 2>/dev/null | tail -n +2 | wc -l
Z620

section "Vultr / public endpoint"
ssh "${SSH_OPTS[@]}" "$VULTR" 'bash -s' 2>&1 <<'VULTR' || printf 'WARN: vultr probe failed\n'
set -u
sub() { printf '\n### %s\n' "$1"; }
kv() { printf '%-26s %s\n' "$1:" "$2"; }

sub "host"
kv hostname "$(hostname)"; kv date_utc "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
uptime
df -h /

sub "security"
sshd -T 2>/dev/null | egrep '^(port|permitrootlogin|passwordauthentication) ' || true
iptables -S 2>/dev/null | grep '^-P' || true

sub "caddy"
kv active "$(systemctl is-active caddy 2>/dev/null || true)"
kv errors_last_200_log_lines "$(journalctl -u caddy -n 200 --no-pager 2>/dev/null | grep -c '"level":"error"' || true)"

sub "headscale"
kv binary "$(command -v headscale 2>/dev/null || echo missing)"
kv service "$(systemctl is-active headscale 2>/dev/null || echo missing)"

sub "updates"
printf 'upgradable_count: '; apt list --upgradable 2>/dev/null | tail -n +2 | wc -l
VULTR

section "Bottom line"
printf '%s\n' \
  "- WARN lines above are the deltas from the inherited map; everything else is evidence." \
  "- report: orients/orient-$STAMP.txt (orients/latest.txt always points at the newest)." \
  "- Old reports are history, not data. To trust a number, read this script next to it."
