# Pop!_OS And Wine Setup

These notes target a Pop!_OS workstation running Sierra Chart through Wine.

## Suggested Layout

```bash
mkdir -p "$HOME/wineprefixes"
export WINEPREFIX="$HOME/wineprefixes/sierrachart"
```

Install and launch Sierra Chart according to Sierra Chart's current Wine guidance. Keep the Wine prefix backed up before major Sierra Chart upgrades.

## Repository Setup

```bash
git clone <repo-url> AxonTrade
cd AxonTrade
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

## ACSIL Sync

```bash
export WINEPREFIX="$HOME/wineprefixes/sierrachart"
bash scripts/sync_to_sierra.sh
```

The script expects Sierra Chart's `ACS_Source` directory to exist under the Wine prefix. It fails if the prefix or source directory cannot be found.

## Backups

```bash
bash scripts/backup_wine_prefix.sh
```

Backups are stored under `$HOME/sierrachart-wine-backups` by default.
