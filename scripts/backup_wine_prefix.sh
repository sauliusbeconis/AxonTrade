#!/usr/bin/env bash
set -euo pipefail

wine_prefix="${WINEPREFIX:-$HOME/wineprefixes/sierrachart}"
backup_dir="${SIERRACHART_WINE_BACKUP_DIR:-$HOME/sierrachart-wine-backups}"

if [[ ! -d "$wine_prefix" ]]; then
  echo "ERROR: Wine prefix does not exist: $wine_prefix" >&2
  echo "Set WINEPREFIX to the Sierra Chart prefix before backing up." >&2
  exit 1
fi

mkdir -p "$backup_dir"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
prefix_parent="$(dirname "$wine_prefix")"
prefix_name="$(basename "$wine_prefix")"
backup_file="$backup_dir/${prefix_name}-${timestamp}.tar.gz"

tar -C "$prefix_parent" -czf "$backup_file" "$prefix_name"

echo "Created Wine prefix backup: $backup_file"
echo "Backups are stored in: $backup_dir"
