#!/usr/bin/env bash
# Replay a server workspace's new commits onto its filtered GitHub branch. Runs detached so a broken ssh pipe cannot interrupt it.
# usage: replay_to_github.sh <workspace> <branch> <base-commit-on-github-side-equivalent>
set -u
W=$1; B=$2; BASE=$3; L=/home/sat/mcrl-records/replay.log; mkdir -p /home/sat/mcrl-records
log(){ echo "$(date -u +%FT%TZ) [$B] $*" >> $L; }
T=/home/sat/.replay-$(echo $B | tr / -); rm -rf $T $T-patches
git clone -q -b $B https://github.com/cedarwud/mcrl-leo-handover.git $T || { log "clone failed"; exit 1; }
git -C $W format-patch -q -o $T-patches $BASE..HEAD >/dev/null 2>&1
n=$(ls $T-patches 2>/dev/null | wc -l); log "patches=$n from $BASE"
[ "$n" -gt 0 ] || { log "nothing to replay"; exit 0; }
git -C $T -c user.name=controller -c user.email=controller@local am -q $T-patches/*.patch 2>>$L || { log "am failed"; exit 1; }
git -C $T push -q origin HEAD:$B 2>>$L && log "pushed $(git -C $T log --oneline -1 | cut -c1-40)"
rm -rf $T-patches
