#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
wine_prefix="${WINEPREFIX:-$HOME/wineprefixes/sierrachart}"

if [[ ! -d "$wine_prefix" ]]; then
  echo "ERROR: Wine prefix does not exist: $wine_prefix" >&2
  echo "Set WINEPREFIX or create the default prefix before syncing." >&2
  exit 1
fi

acs_source="${SIERRACHART_ACS_SOURCE:-}"

if [[ -z "$acs_source" ]]; then
  candidates=(
    "$wine_prefix/drive_c/SierraChart/ACS_Source"
    "$wine_prefix/drive_c/SierraChart64/ACS_Source"
    "$wine_prefix/drive_c/Program Files/Sierra Chart/ACS_Source"
    "$wine_prefix/drive_c/Program Files (x86)/Sierra Chart/ACS_Source"
  )

  for candidate in "${candidates[@]}"; do
    if [[ -d "$candidate" ]]; then
      acs_source="$candidate"
      break
    fi
  done
fi

if [[ -z "$acs_source" || ! -d "$acs_source" ]]; then
  echo "ERROR: Sierra Chart ACS_Source directory was not found." >&2
  echo "Checked WINEPREFIX: $wine_prefix" >&2
  echo "Set SIERRACHART_ACS_SOURCE to the full ACS_Source path if needed." >&2
  exit 1
fi

shopt -s nullglob
sources=("$repo_root"/src/acsil/*.cpp)

if [[ ${#sources[@]} -eq 0 ]]; then
  echo "ERROR: No ACSIL source files found under $repo_root/src/acsil" >&2
  exit 1
fi

for source_file in "${sources[@]}"; do
  destination="$acs_source/$(basename "$source_file")"
  cp "$source_file" "$destination"
  echo "Copied: $destination"
done
