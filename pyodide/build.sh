#!/bin/bash
set -e

export EMSCRIPTEN_VERSION=1.38.30

export PYODIDE_ROOT=$PWD/repo
export PATH=$PYODIDE_ROOT/ccache:$PYODIDE_ROOT/emsdk/emsdk:$PYODIDE_ROOT/emsdk/emsdk/clang/tag-e$EMSCRIPTEN_VERSION/build_tag-e$EMSCRIPTEN_VERSION_64/bin:$PYODIDE_ROOT/emsdk/emsdk/node/8.9.1_64bit/bin:$PYODIDE_ROOT/emsdk/emsdk/emscripten/tag-$EMSCRIPTEN_VERSION:$PYODIDE_ROOT/emsdk/emsdk/binaryen/tag-$EMSCRIPTEN_VERSION_64bit_binaryen/bin:$PATH

export EMSDK=$PYODIDE_ROOT/emsdk/emsdk
export EM_CONFIG=$PYODIDE_ROOT/emsdk/emsdk/.emscripten
export EM_CACHE=$PYODIDE_ROOT/emsdk/emsdk/.emscripten_cache
export EMSCRIPTEN=$PYODIDE_ROOT/emsdk/emsdk/emscripten/tag-$EMSCRIPTEN_VERSION
export BINARYEN_ROOT=$PYODIDE_ROOT/emsdk/emsdk/binaryen/tag-$EMSCRIPTEN_VERSION_64bit_binaryen

make -C repo/emsdk -j4
make -C repo/cpython -j4
make -C repo build/pyodide.asm.js
cp repo/build/pyodide.asm.{js,wasm} build/

export FILEPACKAGER=$PWD/repo/tools/file_packager.py
export PYODIDE_PACKAGE_ABI=1

mkdir -p build
rm -r root || true
mkdir -p root/lib/python3.7

< repo/src/pyodide.js sed -e "s#{{DEPLOY}}##g" | sed -e "s#{{ABI}}#$PYODIDE_PACKAGE_ABI#g" > build/pyodide_dev.js

echo '{"dependencies": {}, "import_name_to_package_name": {}}' > build/packages.json


rsync --delete -r --exclude '__pycache__' \
      --exclude venv --exclude wsgiref --exclude xml --exclude turtledemo --exclude tkinter \
      --exclude test --exclude ensurepip --exclude idlelib --exclude distutils \
      --exclude lib2to3 --exclude pydoc_data --exclude email --exclude multiprocessing \
      --exclude .mypy_cache \
      ./repo/cpython/installs/python-3.7.0/lib/python3.7/ root/lib/python3.7

cp ./repo/src/*.py root/lib/python3.7/
rsync --exclude .mypy_cache --exclude __pycache__ -rv stdlib/ root/lib/python3.7/

python $FILEPACKAGER build/pyodide.asm.data --abi=$PYODIDE_PACKAGE_ABI --lz4 --js-output=build/pyodide.asm.data.js --use-preload-plugins --preload root/lib@lib

#uglifyjs build/pyodide.asm.data.js -o build/pyodide.asm.data.js
