#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_SRC="$ROOT_DIR/bin/pool"
BIN_DIR="${HOME}/.local/bin"
SYSTEMD_USER_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

for cmd in bash ssh rsync jq sha256sum stat find flock; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$cmd" >&2
    printf 'Install the missing dependency and run this installer again.\n' >&2
    exit 1
  fi
done

mkdir -p "$BIN_DIR" "$SYSTEMD_USER_DIR"
install -m 0755 "$BIN_SRC" "$BIN_DIR/pool"
install -m 0644 "$ROOT_DIR/systemd/p2p-filepool-sync.service" "$SYSTEMD_USER_DIR/p2p-filepool-sync.service"
install -m 0644 "$ROOT_DIR/systemd/p2p-filepool-sync.timer" "$SYSTEMD_USER_DIR/p2p-filepool-sync.timer"

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload || true
fi

printf 'Installed: %s\n' "$BIN_DIR/pool"
printf 'If ~/.local/bin is not in PATH, add it to your shell profile.\n'
printf '\nNext steps:\n'
printf '  pool init\n'
printf '  pool peer add <node> <host> [user] [port]\n'
printf '  systemctl --user enable --now p2p-filepool-sync.timer\n'
