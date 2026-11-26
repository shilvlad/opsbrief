#!/usr/bin/env bash
# Consistent SQLite backup from the running OpsBrief Docker volume.
set -Eeuo pipefail

VOLUME="${OPSBRIEF_VOLUME:-opsbrief_opsbrief_data}"
IMAGE="${OPSBRIEF_BACKUP_IMAGE:-opsbrief-api}"
DIR="${OPSBRIEF_BACKUP_DIR:-/var/backups/opsbrief}"

if [[ $(id -u) -ne 0 ]]; then
  echo "Run as root: sudo bash infra/scripts/backup-sqlite.sh" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required" >&2
  exit 1
fi

if ! docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  echo "Volume $VOLUME not found; refusing empty backup" >&2
  exit 1
fi

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Image $IMAGE not found; backup will not pull an unverified image" >&2
  exit 1
fi

install -d -m 0700 -o root -g root "$DIR"
chmod 0700 "$DIR"
TS=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="opsbrief-${TS}.sqlite3"
# Backup is created atomically, never overwriting an existing file.
docker run --rm --pull=never --user 0 \
  --network none \
  --mount "type=volume,source=${VOLUME},target=/source,readonly" \
  --mount "type=bind,source=${DIR},target=/backup" \
  --entrypoint python "$IMAGE" -c '
import os, sqlite3, sys
from pathlib import Path
src = Path("/source/opsbrief.sqlite3")
target = Path("/backup") / sys.argv[1]
temporary = target.with_suffix(".sqlite3.tmp")
if not src.is_file():
    raise SystemExit("ERROR: source SQLite database not found")
if target.exists() or temporary.exists():
    raise SystemExit("ERROR: backup destination already exists")
try:
    with sqlite3.connect(f"file:{src}?mode=ro", uri=True) as source:
        with sqlite3.connect(str(temporary)) as dest:
            source.backup(dest)
    with sqlite3.connect(str(temporary)) as check:
        result = check.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"integrity_check: {result}")
        # Schema check: reject empty or unrelated databases.
        match = check.execute("SELECT count(*) FROM sqlite_master WHERE type = ? AND name = ?", ("table", "briefs")).fetchone()[0]
        if match != 1:
            raise RuntimeError("briefs table is missing")
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)
    print("Backup complete; integrity_check=ok; stored in " + str(target))
finally:
    if temporary.exists():
        temporary.unlink()
' "$BACKUP"
echo "NOTE: Backup is local. Copy it to an encrypted off-host storage for disaster recovery."
