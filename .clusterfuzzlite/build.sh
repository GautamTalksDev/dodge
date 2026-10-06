#!/bin/bash -eu
# sgp4 only (the fuzz targets do not need numpy), installed with hashes.
python3 -m pip install --require-hashes --no-deps -r "$SRC/dodge/.clusterfuzzlite/requirements-fuzz.txt"
for f in "$SRC"/dodge/fuzz/fuzz_*.py; do
  compile_python_fuzzer "$f" --paths "$SRC/dodge/tools"
done
