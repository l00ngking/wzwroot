#!/usr/bin/env bash
# Clone fcitx5-android at the commit the patches were made against and apply them.
#   tools/apply_patches.sh [target-dir]      (default: ./fcitx5-android)
set -euo pipefail

BASE=eb5b50216e70484a009933d9519db76005f1faf3
HERE="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-fcitx5-android}"

git clone https://github.com/fcitx5-android/fcitx5-android.git "$DEST"
cd "$DEST"
git checkout -q "$BASE"
git submodule update --init --recursive
git checkout -q -b liquid-glass
git -c user.name=build -c user.email=build@localhost am "$HERE"/patches/*.patch
echo "Patched. Build it as described in the upstream README, e.g.: ./gradlew assembleRelease"
