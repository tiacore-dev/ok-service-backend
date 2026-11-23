#!/usr/bin/env bash
# Production deployment of a verified release image. Runs on the server from the Compose project directory:
#   ssh host 'cd <path> && bash -s -- <sha> <image> <version> <digest> <run_id>' < scripts/deploy-production.sh
# .release-state is written only after migrations, restart, verification and both statistics rebuilds succeeded;
# a retry that finds it matching a healthy running container does nothing (docs/release-process.md).
set -euo pipefail

# Wrapped in main: bash must read the whole script from stdin before any command can consume stdin.
main() {
  sha="$1" image="$2" version="$3" digest="$4" run_id="$5"
  ref="${image}@${digest}"
  state_file=.release-state
  # Pins web to the verified digest on top of the production files; their volumes and environment stay as they are.
  pin_file=.release-compose.yaml
  compose=(docker compose -f docker-compose.app.yaml -f docker-compose.prod.yaml -f "$pin_file")

  fail() { echo "$*" >&2; exit 1; }
  state_get() { [ -f "$state_file" ] && sed -n "s/^$1=//p" "$state_file" | tail -n1 || true; }
  semver_max() { printf '%s\n%s\n' "$1" "$2" | sort -t. -k1,1n -k2,2n -k3,3n | tail -n1; }

  # Every Compose call below (Alembic, restart, probe, rebuilds) resolves web to exactly $ref.
  pin_web() {
    printf 'services:\n  web:\n    image: %s\n' "$ref" > "$pin_file"
    local resolved
    # Structured config, parsed inside the verified image (no jq/python needed on the host, no network);
    # only services.web.image is printed. `config --images web` would also list web's dependencies.
    resolved="$("${compose[@]}" config --format json \
      | docker run --rm -i --network none --entrypoint python "$ref" \
        -c 'import json, sys; print(json.load(sys.stdin)["services"]["web"]["image"])')" \
      || fail "Cannot resolve web.image from the Compose configuration"
    echo "Compose web.image: ${resolved}"
    [ "$resolved" = "$ref" ] || fail "Compose resolves web to '${resolved}', expected ${ref}; refusing to deploy"
  }

  # The web container runs exactly the image with the release digest.
  running_release() {
    local id expected
    id="$("${compose[@]}" ps -q web)" || return 1
    [ -n "$id" ] || return 1
    expected="$(docker image inspect --format '{{.Id}}' "$ref" 2>/dev/null)" || return 1
    [ "$(docker inspect --format '{{.Image}}' "$id")" = "$expected" ]
  }

  # Ready = /metrics answers and app_info reports the release version; bounded to ~60 s.
  wait_ready() {
    local probe='import sys, urllib.request; body = urllib.request.urlopen("http://127.0.0.1:8000/metrics", timeout=5).read().decode(); sys.exit(0 if f"app_info{{version=\"{sys.argv[1]}\"}}" in body else 1)'
    for _ in $(seq 1 30); do
      "${compose[@]}" exec -T web python -c "$probe" "$version" 2>/dev/null && return 0
      sleep 2
    done
    return 1
  }

  deployed_version="$(state_get VERSION)"
  if [ "$deployed_version" = "$version" ]; then
    [ "$(state_get SHA)" = "$sha" ] && [ "$(state_get DIGEST)" = "$digest" ] \
      || fail "Version ${version} is already deployed from another commit or image; refusing"
    pin_web
    if running_release; then
      wait_ready || fail "Release ${version} is deployed but web is not ready; not reporting it as deployed"
      echo "Release ${version} is already deployed, running and ready; skipping migrations and rebuilds."
      echo "DEPLOY_RESULT=already-deployed"
      exit 0
    fi
    echo "Release ${version} was deployed but is not running; redeploying."
  elif [ -n "$deployed_version" ] && [ "$(semver_max "$deployed_version" "$version")" != "$version" ]; then
    fail "Production already runs newer release ${deployed_version}; refusing to deploy ${version}"
  fi

  # Compose files and migrations come from the checkout: it must be exactly the image commit.
  # Operator edits to tracked files are left alone; untracked/ignored files (.env, logs, state) are fine.
  if ! git diff --quiet || ! git diff --cached --quiet; then
    fail "Production checkout has staged or unstaged changes to tracked files; resolve them first"
  fi
  git fetch -q origin master
  git merge -q --ff-only "$sha"
  [ "$(git rev-parse HEAD)" = "$sha" ] || fail "Production checkout is not ${sha}; aborting"

  docker pull -q "$ref" >/dev/null
  docker pull -q "${image}:${version}" >/dev/null
  [ "$(docker image inspect --format '{{.Id}}' "${image}:${version}")" = "$(docker image inspect --format '{{.Id}}' "$ref")" ] \
    || fail "${image}:${version} does not match the verified digest ${digest}"
  pin_web

  # TAG keeps manual `docker compose` runs (without the pin file) on the same release.
  [ -f .env ] || touch .env
  if grep -q '^TAG=' .env; then
    sed -i "s/^TAG=.*/TAG=${version}/" .env
  else
    # Terminate an unterminated last entry first, so it is not merged with TAG.
    [ -s .env ] && [ -n "$(tail -c1 .env)" ] && echo >> .env
    echo "TAG=${version}" >> .env
  fi

  "${compose[@]}" run --rm web alembic upgrade head
  "${compose[@]}" up -d --force-recreate web
  docker image prune -f >/dev/null

  running_release || fail "web is not running ${ref}"
  wait_ready || fail "web did not become ready with app_info version ${version}"

  "${compose[@]}" run --rm web flask --app app:create_app rebuild-project-work-statistics
  "${compose[@]}" run --rm web flask --app app:create_app rebuild-project-material-statistics

  printf 'VERSION=%s\nSHA=%s\nDIGEST=%s\nRUN_ID=%s\nDEPLOYED_AT=%s\n' \
    "$version" "$sha" "$digest" "$run_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${state_file}.tmp"
  mv "${state_file}.tmp" "$state_file"
  echo "DEPLOY_RESULT=deployed"
}

main "$@"
