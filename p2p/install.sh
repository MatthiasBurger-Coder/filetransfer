#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
LIB_DIR="${HOME}/.local/lib/p2p-filepool"
SYSTEMD_USER_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

for cmd in bash ssh rsync jq sha256sum stat find flock; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$cmd" >&2
    printf 'Install the missing dependency and run this installer again.\n' >&2
    exit 1
  fi
done

mkdir -p "$BIN_DIR" "$LIB_DIR" "$SYSTEMD_USER_DIR"
install -m 0755 "$ROOT_DIR/bin/pool" "$LIB_DIR/pool-core"
install -m 0755 "$ROOT_DIR/bin/pool-wrapper" "$BIN_DIR/pool"
install -m 0644 "$ROOT_DIR/systemd/p2p-filepool-sync.service" "$SYSTEMD_USER_DIR/p2p-filepool-sync.service"
install -m 0644 "$ROOT_DIR/systemd/p2p-filepool-sync.timer" "$SYSTEMD_USER_DIR/p2p-filepool-sync.timer"

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload || true
fi

printf 'Installed CLI: %s\n' "$BIN_DIR/pool"
printf 'Installed core: %s\n' "$LIB_DIR/pool-core"
printf 'If ~/.local/bin is not in PATH, add it to your shell profile.\n'
printf '\nNext steps:\n'
printf '  pool init\n'
printf '  pool peer add <node> <host> [user] [port]\n'
printf '  systemctl --user enable --now p2p-filepool-sync.timer\n'
