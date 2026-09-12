set -u
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
P=/home/u24/papers/mcrl-leo-handover/.venv/bin/python
R=/home/u24/papers/mcrl-leo-handover-mc2
B=$R/.scratch/mc2/B
cd $B
D3k10=ckpt/E0-4-D3-T0-equal_share-k10-policy-ep00100.pt
D3k11=ckpt/E0-4-D3-T0-equal_share-k11-policy-ep00100.pt
V1k10="ckpt/E0-10-MC2-v1-A+B-equal_share-k10-policy-ep00100.pt"
V1k11="ckpt/E0-10-MC2-v1-A+B-equal_share-k11-policy-ep00100.pt"
V2k10="ckpt/E0-10-MC2-v2-A+B-equal_share-k10-policy-ep00100.pt"
V2k11="ckpt/E0-10-MC2-v2-A+B-equal_share-k11-policy-ep00100.pt"
DV() { echo "ep100/$1/devval-ep00100.json"; }
go() { # name host also devvaldir
  $P b_output_change.py --repo $R --policy "$2" --also "$3" --devval "$(DV "$4")" \
     --judge --episodes 24 --out "out/$1.json" > "out/$1.log" 2>&1
  echo "done $1 rc=$?" >> out/progress.txt
}
: > out/progress.txt
go host-D3T0-k10 "$D3k10" "$V1k10" E0-4-D3-T0-equal_share-k10 &
go host-D3T0-k11 "$D3k11" "$V1k11" E0-4-D3-T0-equal_share-k11 &
go host-v1FULL-k10 "$V1k10" "$D3k10" "E0-10-MC2-v1-A+B-equal_share-k10" &
wait
go host-v1FULL-k11 "$V1k11" "$D3k11" "E0-10-MC2-v1-A+B-equal_share-k11" &
go host-v2FULL-k10 "$V2k10" "$D3k10" "E0-10-MC2-v2-A+B-equal_share-k10" &
go host-v2FULL-k11 "$V2k11" "$D3k11" "E0-10-MC2-v2-A+B-equal_share-k11" &
wait
echo ALLDONE >> out/progress.txt
