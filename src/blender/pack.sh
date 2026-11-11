#!/bin/bash
cd /home/claude/mapgen
for k in ${@:-globe coin chip bulb lens stack plane}; do
  npx gltf-transform optimize /home/claude/b3d/out/$k.glb /home/claude/v1/site/assets/models/$k.glb --compress meshopt --texture-compress webp --texture-size 1024 --flatten false --join false --palette false --simplify false --instance false >/dev/null 2>&1 || echo FAIL $k
done
ls -la /home/claude/v1/site/assets/models | awk 'NR>3{s+=$5; print $5,$9} END{print "total",s}'
