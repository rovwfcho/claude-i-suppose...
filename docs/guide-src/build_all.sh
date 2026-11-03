#!/bin/sh
# Rebuild docs/assembly_guide_en.pdf, docs/assembly_guide_bg.pdf, preview/renders.png and preview/explained.png
# from case.py.
# Needs python3 (manifold3d numpy pillow), node with playwright and its Chromium, and network access
# to registry.npmjs.org the first time (for three.js r160).
set -e
cd "$(dirname "$0")"
python3 text_en.py
python3 text_bg.py
python3 make_specs.py
python3 make_renders.py specs
python3 export_scene.py .
if [ ! -f three.module.js ] || [ ! -f STLLoader.js ]; then
  curl -sSf -o three.tgz https://registry.npmjs.org/three/-/three-0.160.0.tgz
  tar -xzf three.tgz package/build/three.module.js package/examples/jsm/loaders/STLLoader.js
  cp package/build/three.module.js package/examples/jsm/loaders/STLLoader.js .
  rm -rf package three.tgz
fi
python3 -m http.server 8766 >/dev/null 2>&1 &
SERVER=$!
trap 'kill $SERVER' EXIT
sleep 1
node shoot.js renders_specs.json
python3 make_renders.py compose
python3 make_explained.py specs
node shoot.js explained_specs.json
python3 make_explained.py compose
node shoot.js specs.json
mkdir -p out
python3 build.py en bg
node topdf.js "$PWD/out/guide_en.html=$PWD/../assembly_guide_en.pdf" "$PWD/out/guide_bg.html=$PWD/../assembly_guide_bg.pdf"
echo "done"
