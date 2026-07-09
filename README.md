# Filetransfer

`filetransfer` creates fast, ordered transfer packages for large data sets.
It streams a source directory through `tar`, optionally through `zstd`, splits
the byte stream into fixed-size chunks, and wraps each chunk as a real `.7z`
container with `7z -mx=0`.

It is not a classic 7z multi-volume archive. The `.7z` files are transport
containers around stream chunks. Restore verifies the manifest, extracts every
payload in order, concatenates the payload stream, and feeds it back into
`zstd -d` and `tar`.

## Requirements

- Python 3.10+
- `tar`
- one of `7z`, `7zz`, or `7za`
- optional: `zstd`

## Pack

```bash
python -m filetransfer pack /data/bigfolder /transfer \
  --prefix bigfolder-transfer \
  --chunk-size 100M \
  --zstd
```

After installing the project, the same command is available as:

```bash
filetransfer pack /data/bigfolder /transfer \
  --prefix bigfolder-transfer \
  --chunk-size 100M \
  --zstd
```

This writes files like:

```text
bigfolder-transfer-000001.7z
bigfolder-transfer-000002.7z
bigfolder-transfer-manifest.7z
```

## Restore

```bash
python -m filetransfer restore /transfer/bigfolder-transfer-manifest.7z /restore-target
```

If all package checksums match, the byte stream is reconstructed exactly.
The restored files are produced by `tar`; existing files may be overwritten by
`tar` according to the system tar implementation's normal behavior.

## Notes

- `--zstd` uses fast streaming compression. Use `--no-zstd` for a plain tar
  stream.
- Each data `.7z` package contains one file named `payload.bin`.
- The final `*-manifest.7z` package contains one file named `manifest.json`.
- The manifest records package SHA-256, payload SHA-256, sizes, stream settings,
  and the exact package order.
- Packing creates one temporary raw chunk at a time in the transfer directory
  and deletes it after the corresponding `.7z` container is verified.

## Code Structure

- `filetransfer/cli.py`: thin process entry point and error handling.
- `filetransfer/arguments.py`: command-line parser and subcommand wiring.
- `filetransfer/commands/`: top-level workflows for `pack`, `restore`, and `verify`.
- `filetransfer/core/`: transfer-domain logic such as manifests, `.7z` containers, and streams.
- `filetransfer/system/`: system helpers for tools, processes, checksums, validation, and errors.
