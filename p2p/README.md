# P2P File Pool

A small decentralized file-pool for Linux nodes using shell scripts, SSH, rsync and JSON metadata.

## Model

- Every node owns a local file directory.
- Files stay on the node that owns them.
- Only metadata indexes are synchronized between peers.
- If a node is offline, its unique files are temporarily unavailable.
- If the same content hash exists on another online node, `pool get` can use that peer instead.
- There is no central storage server and no authoritative central index.

Each peer publishes its own JSON index under `~/.local/share/p2p-filepool/indexes/<node>.json`.

## Requirements

- bash
- ssh
- rsync
- jq
- sha256sum
- find
- stat
- systemd (optional, for automatic synchronization)

Debian/Ubuntu example:

```bash
sudo apt install rsync jq openssh-client
```

## Quick start

On every node:

```bash
cd p2p
./install.sh
pool init
```

The default shared directory is:

```text
~/FilePool
```

You can override it before running `pool init`:

```bash
export POOL_SHARE_DIR=/srv/filepool
pool init
```

### Add peers

On node-a:

```bash
pool peer add node-b 192.168.1.20 alice 22
pool peer add node-c 192.168.1.30 alice 22
```

On the other nodes add the corresponding peers as well. Peer configuration is intentionally decentralized.

SSH key authentication is strongly recommended:

```bash
ssh-copy-id alice@192.168.1.20
```

### Publish files

Put a file into `~/FilePool` or use:

```bash
pool publish /path/to/file.iso
```

Then scan and synchronize:

```bash
pool scan
pool sync
```

### Browse the pool

```bash
pool ls
pool find ubuntu.iso
pool status
```

### Retrieve a file

```bash
pool get ubuntu.iso
```

By default it is copied into the current directory. You can provide a destination:

```bash
pool get ubuntu.iso /tmp/
```

`pool get` prefers a reachable peer. The SHA-256 hash is verified after transfer.

## Commands

```text
pool init
pool scan
pool sync
pool status
pool ls
pool find <pattern>
pool get <name-or-hash> [destination]
pool publish <file>
pool peer list
pool peer add <node> <host> [user] [port]
pool peer remove <node>
```

## Files

```text
~/.config/p2p-filepool/config
~/.config/p2p-filepool/peers.conf
~/.local/share/p2p-filepool/indexes/*.json
~/FilePool/
```

`peers.conf` is tab-separated:

```text
node-b\t192.168.1.20\talice\t22
node-c\t192.168.1.30\talice\t22
```

## Automatic metadata synchronization

`install.sh` installs a user-level systemd service and timer. Enable it with:

```bash
systemctl --user enable --now p2p-filepool-sync.timer
```

Check it with:

```bash
systemctl --user status p2p-filepool-sync.timer
journalctl --user -u p2p-filepool-sync.service
```

The timer runs `pool scan` followed by `pool sync` every minute.

## Availability semantics

This V1 does not automatically replicate file payloads. Availability is therefore honest and simple:

- one copy + owner offline -> unavailable
- two copies with the same SHA-256 + one owner online -> available
- metadata remains visible even while an owner is offline

Automatic replica policies can be added later without changing the index model.

## Security

The implementation uses normal SSH access. It does not bypass firewall policy, create reverse tunnels or expose a daemon port. Restrict SSH users and keys as you would for any other administrative access.
