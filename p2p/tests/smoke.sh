#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POOL="$ROOT_DIR/bin/pool-wrapper"
TMP_HOME="$(mktemp -d)"
trap 'rm -rf "$TMP_HOME"' EXIT

export HOME="$TMP_HOME"
export XDG_CONFIG_HOME="$TMP_HOME/.config"
export XDG_DATA_HOME="$TMP_HOME/.local/share"
export POOL_NODE_NAME="smoke-node"
export POOL_SHARE_DIR="$TMP_HOME/FilePool"
export POOL_CORE="$ROOT_DIR/bin/pool"

"$POOL" init

printf 'hello p2p\n' >"$TMP_HOME/example.txt"
"$POOL" publish "$TMP_HOME/example.txt"

INDEX="$XDG_DATA_HOME/p2p-filepool/indexes/smoke-node.json"
[[ -f "$INDEX" ]]
[[ "$(jq -r '.node' "$INDEX")" == "smoke-node" ]]
[[ "$(jq '.files | length' "$INDEX")" -eq 1 ]]
[[ "$(jq -r '.files[0].name' "$INDEX")" == "example.txt" ]]

"$POOL" find example.txt | grep -q 'example.txt'
"$POOL" get example.txt "$TMP_HOME/download"
cmp "$POOL_SHARE_DIR/example.txt" "$TMP_HOME/download/example.txt"

printf 'P2P file-pool smoke test: OK\n'
