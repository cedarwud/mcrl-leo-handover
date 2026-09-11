# usage: waitfor.sh EPISODE NRUNS MAXMIN  -> exits when NRUNS runs have a reading at EPISODE, or any failure/stop, or timeout
EP=$1; N=$2; MAX=$3
for i in $(seq 1 $((MAX*2))); do
  r=$(ssh sat "cd /home/sat/mcrl-v025-cf3-pilot-ws/runs && grep -l '\"episode\": $EP,' */readings.jsonl 2>/dev/null | wc -l; grep -l -E '\"status\": \"(failed|stopped-learning-check)\"' */status.json 2>/dev/null | wc -l" 2>/dev/null | tr '\n' ' ')
  set -- $r
  if [ "${1:-0}" -ge "$N" ] || [ "${2:-0}" -gt 0 ]; then echo "reached: runs_with_reading=$1 failed_or_stopped=$2"; exit 0; fi
  sleep 30
done
echo "timeout: $r"
