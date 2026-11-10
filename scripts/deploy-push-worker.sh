#!/usr/bin/env bash
# Run on the dev host from the Compose project directory after migrations.
set -euo pipefail

compose=(docker compose -f docker-compose.app.yaml)

# Compose one-off containers are not replaced by `compose up`.
if [[ -n "$(docker ps -q --filter 'name=^/ok-service-backend-dev-push-worker-run-')" ]]; then
  echo 'A manual push-worker is still running; stop it using the runbook before deploying.' >&2
  exit 1
fi

# Run as the worker UID, with its mounts, without printing configuration values.
"${compose[@]}" run --rm --no-deps -T --entrypoint python push-worker -c '
import json
from pathlib import Path
from config import Config

if (Config.PUSH_PROVIDER or "").strip().lower() != "fcm":
    raise SystemExit("push-worker requires PUSH_PROVIDER=fcm")
if not (Config.FCM_PROJECT_ID or "").strip():
    raise SystemExit("push-worker requires FCM_PROJECT_ID")
path = Path(Config.GOOGLE_APPLICATION_CREDENTIALS or "").resolve()
if not path.is_relative_to(Path("/app/secrets")) or not path.is_file():
    raise SystemExit("push-worker credentials must be a file under /app/secrets")
try:
    with path.open(encoding="utf-8") as credentials:
        json.load(credentials)
except (OSError, ValueError):
    raise SystemExit("push-worker credentials are unreadable or invalid JSON") from None
if not all(value > 0 for value in (
    Config.PUSH_WORKER_BATCH_SIZE, Config.PUSH_WORKER_POLL_INTERVAL_SECONDS,
    Config.PUSH_WORKER_LEASE_SECONDS, Config.PUSH_WORKER_MAX_ATTEMPTS,
    Config.PUSH_WORKER_RETRY_BASE_SECONDS, Config.PUSH_WORKER_RETRY_MAX_SECONDS,
)):
    raise SystemExit("push-worker settings must be positive")
'

"${compose[@]}" up -d --no-deps --force-recreate --scale push-worker=1 push-worker
container_id=$("${compose[@]}" ps -q push-worker)
if [[ -z "$container_id" ]]; then
  echo 'push-worker container was not created' >&2
  exit 1
fi
# Give immediate failures and restart loops time to become visible.
sleep 10
state=$(docker inspect --format '{{.State.Status}} {{.RestartCount}}' "$container_id")
if [[ "$state" != 'running 0' ]]; then
  echo "push-worker failed startup (state/restarts: $state); inspect its logs." >&2
  exit 1
fi
