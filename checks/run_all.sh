#!/bin/sh
# Rebuild the STL files and run every check. Needs: pip install manifold3d trimesh numpy scipy shapely rtree networkx matplotlib pillow
cd "$(dirname "$0")/.." || exit 1
status=0
for s in verify.py checks/round1.py checks/round2.py checks/round3.py checks/round4.py checks/round5.py \
         checks/round6.py checks/round7.py checks/round8.py checks/round9.py checks/round10.py \
         checks/round11.py checks/round12.py checks/round13.py checks/round14.py checks/round15.py \
         checks/round16.py checks/round17.py checks/round18.py \
         checks/round19.py checks/round20.py \
         checks/round21.py checks/round22.py \
         checks/round23.py checks/round28.py checks/round29.py \
         checks/round30.py checks/round31.py checks/round32.py \
         checks/round33.py checks/round34.py checks/round35.py \
         checks/round36.py checks/round37.py checks/round38.py \
         checks/round39.py checks/round40.py checks/round41.py \
         checks/round42.py checks/round43.py checks/round44.py \
         checks/round45.py checks/round46.py checks/round47.py checks/round48.py \
         checks/round49.py checks/round50.py checks/round51.py checks/round52.py; do
  echo "=== $s"
  python3 "$s" || status=1
done
exit $status
