#!/bin/bash
# Fill the MC2 ep-100 root to 16 runs, 8 workers at a time.  Each ssh call is SHORT
# (count, then one launcher invocation); the waiting loop is local, so no remote shell
# is ever asked to wait and no launch can be silently skipped.
# One stdout line per event.  Exits when all 16 runs have a status.json.
set -u
WS=/home/sat/mcrl-v025-mc2-ws
CAP=8

count_live () {
    timeout 60 ssh sat 'c=0; for p in /proc/[0-9]*; do e=$(readlink $p/exe 2>/dev/null); case "$e" in *python*) w=$(readlink $p/cwd 2>/dev/null); case "$w" in /home/sat/*) c=$((c+1));; esac;; esac; done; echo $c' 2>/dev/null
}
count_status () {
    timeout 60 ssh sat "ls -d $WS/runs-ep100/*/status.json 2>/dev/null | wc -l" 2>/dev/null
}

for round in $(seq 1 120); do
    live=$(count_live); case "${live:-}" in ''|*[!0-9]*) live=99;; esac
    done_n=$(count_status); case "${done_n:-}" in ''|*[!0-9]*) done_n=0;; esac
    if [ "$done_n" -ge 16 ]; then
        echo "ALL 16 ep-100 runs have a status.json (live=$live); wave filling done"
        exit 0
    fi
    slots=$((CAP - live))
    if [ "$slots" -gt 0 ]; then
        out=$(timeout 240 ssh sat "cd $WS && ./ep100.sh --launch-limit $slots 2>&1")
        started=$(printf '%s\n' "$out" | grep -c '^  launched ')
        if [ "$started" -gt 0 ]; then
            printf '%s\n' "$out" | grep -E '^  launched |^\[.*all [0-9]+ launched|FAILED TO START|refusing' \
                | sed "s/^/WAVE(round $round, live=$live, slots=$slots): /"
        elif [ $((round % 10)) -eq 0 ]; then
            echo "heartbeat round $round: live=$live slots=$slots, $done_n/16 started, nothing startable"
        fi
    elif [ $((round % 10)) -eq 0 ]; then
        echo "heartbeat round $round: live=$live (cap $CAP), $done_n/16 started; waiting"
    fi
    sleep 90
done
echo "wave filler gave up after 120 rounds"
exit 1
