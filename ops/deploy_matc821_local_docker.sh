#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  deploy_matc821_local_docker.sh [options]

Options:
  --package-dir PATH   Source folder for docassemble-MATCGuardiansCarePlanReportMpc821-main
  --server URL         Docassemble server URL (default: $DA_SERVER or http://localhost:5050)
  --api-key KEY        Docassemble API key (default: $DA_API_KEY)
  --container NAME     Docker container name (default: $DA_CONTAINER_NAME or local compose name)
  --python PATH        Python interpreter for package build
  --skip-upload        Skip API /api/package upload step
  --skip-reinstall     Skip in-container pip --force-reinstall step
  --skip-restart       Skip Docker restart step
  -h, --help           Show this help
USAGE
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PACKAGE_DIR="$REPO_ROOT/../docassemble-MATCGuardiansCarePlanReportMpc821-main"
SERVER="${DA_SERVER:-http://localhost:5050}"
API_KEY="${DA_API_KEY:-}"
CONTAINER_NAME="${DA_CONTAINER_NAME:-docassemble-matc1auncontesteddivorce-docassemble-1}"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv-codex/bin/python}"

SKIP_UPLOAD=0
SKIP_REINSTALL=0
SKIP_RESTART=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --package-dir)
      PACKAGE_DIR="$2"
      shift 2
      ;;
    --server)
      SERVER="$2"
      shift 2
      ;;
    --api-key)
      API_KEY="$2"
      shift 2
      ;;
    --container)
      CONTAINER_NAME="$2"
      shift 2
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --skip-upload)
      SKIP_UPLOAD=1
      shift
      ;;
    --skip-reinstall)
      SKIP_REINSTALL=1
      shift
      ;;
    --skip-restart)
      SKIP_RESTART=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$API_KEY" && "$SKIP_UPLOAD" -eq 0 ]]; then
  echo "DA_API_KEY (or --api-key) is required unless --skip-upload is used." >&2
  exit 1
fi

if [[ ! -d "$PACKAGE_DIR" ]]; then
  echo "Package directory not found: $PACKAGE_DIR" >&2
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi

if [[ -z "$PYTHON_BIN" ]]; then
  echo "No Python interpreter found for package build." >&2
  exit 1
fi

TMPDIR="$(mktemp -d /tmp/matc821deploy.XXXXXX)"
cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

echo "==> Building clean MATC821 package from: $PACKAGE_DIR"
rsync -a --exclude '._*' --exclude '.git' --exclude 'dist' "$PACKAGE_DIR/" "$TMPDIR/src/"
(
  cd "$TMPDIR/src"
  "$PYTHON_BIN" setup.py sdist --formats=zip >/tmp/matc821_deploy_build.log 2>&1
)

ZIP_FILE="$(ls -1 "$TMPDIR"/src/dist/docassemble_matcguardianscareplanreportmpc821-*.zip | sort | tail -n1)"
ZIP_BASENAME="$(basename "$ZIP_FILE")"
VERSION="$(echo "$ZIP_BASENAME" | sed -E 's/^docassemble_matcguardianscareplanreportmpc821-([0-9.]+)\.zip$/\1/')"
OUTPUT_ZIP="$PACKAGE_DIR/docassemble-MATCGuardiansCarePlanReportMpc821-${VERSION}-nogit.zip"
cp "$ZIP_FILE" "$OUTPUT_ZIP"

echo "==> Built zip: $OUTPUT_ZIP"

if [[ "$SKIP_UPLOAD" -eq 0 ]]; then
  echo "==> Uploading package via API: $SERVER/api/package"
  UPLOAD_RESPONSE="$(curl -fsS -X POST "$SERVER/api/package" \
    -F "key=$API_KEY" \
    -F "zip=@${ZIP_FILE};type=application/zip")"

  TASK_ID="$(python3 - <<PY
import json
resp = json.loads("""$UPLOAD_RESPONSE""")
print(resp.get("task_id", ""))
PY
)"
  if [[ -z "$TASK_ID" ]]; then
    echo "Upload response did not include task_id: $UPLOAD_RESPONSE" >&2
    exit 1
  fi

  echo "==> Waiting for package update task: $TASK_ID"
  for _ in {1..60}; do
    STATUS_JSON="$(curl -fsS "$SERVER/api/package_update_status?key=$API_KEY&task_id=$TASK_ID")"
    STATUS="$(python3 - <<PY
import json
data = json.loads("""$STATUS_JSON""")
print(data.get("status",""))
PY
)"
    if [[ "$STATUS" == "completed" ]]; then
      echo "    status=completed"
      break
    fi
    if echo "$STATUS_JSON" | grep -q '"error"'; then
      echo "Package update failed: $STATUS_JSON" >&2
      exit 1
    fi
    sleep 2
  done
fi

if [[ "$SKIP_REINSTALL" -eq 0 ]]; then
  echo "==> Force-reinstalling inside container: $CONTAINER_NAME"
  docker cp "$ZIP_FILE" "$CONTAINER_NAME:/tmp/$ZIP_BASENAME"
  docker exec "$CONTAINER_NAME" bash -lc \
    "/usr/share/docassemble/local3.12/bin/pip install --no-deps --force-reinstall /tmp/$ZIP_BASENAME"
fi

if [[ "$SKIP_RESTART" -eq 0 ]]; then
  echo "==> Restarting container: $CONTAINER_NAME"
  docker restart "$CONTAINER_NAME" >/dev/null
fi

echo "==> Waiting for server response: $SERVER"
for _ in {1..90}; do
  CODE="$(curl -s -o /dev/null -w '%{http_code}' "$SERVER" || true)"
  if [[ "$CODE" =~ ^(200|301|302|303|307|308|401|403|404)$ ]]; then
    echo "    server status code: $CODE"
    break
  fi
  sleep 2
done

echo "Done."
echo "Package: $OUTPUT_ZIP"
