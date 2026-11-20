#!/usr/bin/env bash
# Production release steps for GitHub Actions (docs/release-process.md). Run from the repository root.
#   release-ci.sh select  <image> <sha>                    -> state=/version=/digest= lines for $GITHUB_OUTPUT
#     Same call for the build and the deploy-time recheck. If master moved past <sha>, the run continues only
#     when <sha> is still on master, no release exists outside it, and it owns the tag vX.Y.Z or image X.Y.Z.
#   release-ci.sh promote <image> <version> <digest>       -> gives the candidate digest the Docker tag <version>
#   release-ci.sh publish <image> <version> <digest> <sha> -> annotated tag vX.Y.Z + GitHub Release
#   release-ci.sh reschedule                               -> queue a run for the master tip (after state=outdated)
# state: outdated | none (nothing to release) | released (tag exists) | resume (image X.Y.Z of this commit exists) | new
set -euo pipefail

VERSION_SCRIPT="$(dirname "$0")/release-version.sh"

fail() { echo "$*" >&2; exit 1; }

# Manifest digest of $1. Exit code 2 only when the registry says this tag does not exist; anything else is a failure.
registry_digest() {
  local out d
  if out="$(docker buildx imagetools inspect "$1" 2>&1)"; then
    d="$(printf '%s\n' "$out" | awk '$1 == "Digest:" { print $2; exit }')"
    case "$d" in sha256:*) echo "$d"; return 0 ;; esac
    echo "Cannot parse digest for $1: $out" >&2
    return 1
  fi
  case "$out" in *"$1: not found"*) return 2 ;; esac
  echo "Cannot check registry for $1: $out" >&2
  return 1
}

image_label() { docker buildx imagetools inspect "$1" --format "{{index .Image.Config.Labels \"$2\"}}"; }

# Annotated SemVer release tags (same rule as release-version.sh) matching for-each-ref filters.
release_tags() {
  git for-each-ref --format='%(objecttype) %(refname:strip=2)' "$@" refs/tags \
    | awk '$1 == "tag" { print $2 }' \
    | grep -E '^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$' || true
}

# Fetches origin master and prints its commit; captured before any other fetch rewrites FETCH_HEAD.
fetch_master() { git fetch -q origin refs/heads/master && git rev-parse FETCH_HEAD; }

select_release() {
  local image="$1" sha="$2" tip master version state=new digest="" rc=0 rev ver superseded=""
  tip="$(git ls-remote --exit-code origin refs/heads/master | cut -f1)" || fail "Cannot read origin master"
  if [ "$tip" != "$sha" ]; then
    # Master moved on. This run may continue only if it already owns a promoted or tagged version
    # (an interrupted release); otherwise the newer run releases these commits.
    superseded=1
    master="$(fetch_master)" || fail "Cannot fetch origin master"
    git fetch -q --force --tags origin
    if ! git merge-base --is-ancestor "$sha" "$master"; then
      echo "Superseded: ${sha} is no longer on master." >&2
      printf 'state=outdated\n'
      return
    fi
    if [ -n "$(release_tags --no-merged "$sha")" ]; then
      echo "Superseded: a newer release exists outside ${sha}; never rolling back." >&2
      printf 'state=outdated\n'
      return
    fi
  fi
  version="$(sh "$VERSION_SCRIPT" next)"
  if [ -z "$version" ]; then
    echo "No feat/fix/perf/breaking commits since the last release: nothing to deploy or publish." >&2
    if [ -n "$superseded" ]; then printf 'state=outdated\n'; else printf 'state=none\n'; fi
    return
  fi
  # `next` returns an existing version only when its tag points at HEAD.
  git rev-parse -q --verify "refs/tags/v${version}" >/dev/null && state=released

  digest="$(registry_digest "${image}:${version}")" || rc=$?
  case "$rc" in
    0)
      # Labels come from the resolved digest, so a tag moved after the lookup cannot vouch for it.
      rev="$(image_label "${image}@${digest}" org.opencontainers.image.revision)"
      ver="$(image_label "${image}@${digest}" org.opencontainers.image.version)"
      if [ "$rev" != "$sha" ] || [ "$ver" != "$version" ]; then
        if [ -n "$superseded" ] && [ "$state" = new ]; then
          echo "Superseded: image ${version} belongs to ${rev:-another commit}, not ${sha}." >&2
          printf 'state=outdated\n'
          return
        fi
        fail "Image ${version} (${digest}) has revision=${rev:-none} version=${ver:-none}, not ${sha}/${version}." \
          "See 'Незавершённый релиз' in docs/release-process.md."
      fi
      [ "$state" = new ] && state=resume
      ;;
    2)
      [ "$state" = released ] && fail "v${version} is tagged but image ${version} is missing from the registry"
      if [ -n "$superseded" ]; then
        echo "Superseded: master is at ${tip} and ${sha} has no promoted image; the newer run releases it." >&2
        printf 'state=outdated\n'
        return
      fi
      ;;
    *) exit 1 ;;
  esac
  [ -n "$superseded" ] && echo "master moved ahead to ${tip}; finishing release ${version} owned by ${sha}." >&2
  echo "Production version ${version}: ${state}" >&2
  printf 'state=%s\nversion=%s\ndigest=%s\n' "$state" "$version" "$digest"
}

promote() {
  local image="$1" version="$2" digest="$3" existing rc=0
  case "$digest" in sha256:*) ;; *) fail "Invalid candidate digest '${digest}'" ;; esac
  existing="$(registry_digest "${image}:${version}")" || rc=$?
  case "$rc" in
    0) [ "$existing" = "$digest" ] || fail "Image ${version} already exists with digest ${existing}; not overwriting" ;;
    # --prefer-index=false copies the single candidate manifest as is, so the digest does not change.
    2) docker buildx imagetools create --prefer-index=false -t "${image}:${version}" "${image}@${digest}" ;;
    *) exit 1 ;;
  esac
  [ "$(registry_digest "${image}:${version}")" = "$digest" ] || fail "Image ${version} does not resolve to ${digest} after promotion"
}

publish() {
  local image="$1" version="$2" digest="$3" sha="$4" tag="v$2" remote rc=0 api code notes master
  [ "$(git rev-parse HEAD)" = "$sha" ] || fail "Checkout is not ${sha}"
  sh "$VERSION_SCRIPT" check-latest "$version"

  remote="$(git ls-remote --exit-code origin "refs/tags/${tag}" | cut -f1)" || rc=$?
  case "$rc" in
    0)
      # release-version.sh force-fetched tags, so the remote tag object is available locally.
      [ "$(git cat-file -t "$remote")" = tag ] || fail "${tag} exists but is not an annotated tag; not moving it"
      [ "$(git rev-parse "${remote}^{commit}")" = "$sha" ] || fail "${tag} exists on another commit; tags are never moved"
      echo "Tag ${tag} already exists on ${sha}." >&2
      ;;
    2)
      # A retry may run after master was rewritten; never create the highest tag on a commit master dropped.
      master="$(fetch_master)" || fail "Cannot fetch origin master"
      git merge-base --is-ancestor "$sha" "$master" || fail "${sha} is no longer on master; not creating ${tag}"
      git tag -a "$tag" -m "Release ${tag}" "$sha"
      git push origin "refs/tags/${tag}"
      ;;
    *) fail "Cannot read tags from origin" ;;
  esac

  api="${GITHUB_API_URL:-https://api.github.com}/repos/${GITHUB_REPOSITORY:?}/releases"
  local auth=(-H "Authorization: Bearer ${GITHUB_TOKEN:?}" -H "Accept: application/vnd.github+json")
  code="$(curl -sS -o /dev/null -w '%{http_code}' "${auth[@]}" "${api}/tags/${tag}")" || true
  case "$code" in
    200) echo "Release ${tag} already published." >&2; return ;;
    404) ;;
    *) fail "Cannot read GitHub Release ${tag} (HTTP ${code:-none}); check token permissions" ;;
  esac

  notes="$(sh "$VERSION_SCRIPT" notes "$version")"
  # shellcheck disable=SC2016  # backticks are Markdown
  printf '%s\n\n---\n\n- Commit: `%s`\n- Image: `%s:%s`\n- Digest: `%s`\n- Actions run: %s\n' \
    "$notes" "$sha" "$image" "$version" "${digest:-n/a}" \
    "${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID:-unknown}" > release_notes.md
  jq -n --arg tag "$tag" --rawfile body release_notes.md '{tag_name: $tag, name: $tag, body: $body}' \
    | curl -sS --fail-with-body -o /dev/null -X POST "${auth[@]}" -d @- "$api"
  echo "Published ${tag}." >&2
}

# GitHub keeps one pending run per concurrency group: a retried old run can displace the pending run of the
# master tip. A superseded run therefore queues a fresh run for the tip unless the tip is already released.
reschedule() {
  local tip
  tip="$(git ls-remote --exit-code origin refs/heads/master | cut -f1)" || fail "Cannot read origin master"
  if git ls-remote --tags origin | awk -v tip="$tip" '$1 == tip { print $2 }' \
    | grep -qE '^refs/tags/v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\^\{\}$'; then
    echo "master tip ${tip} is already released; nothing to reschedule." >&2
    return
  fi
  gh workflow run "${WORKFLOW_FILE:-deploy.yml}" --ref master
  echo "Queued a production run for the master tip ${tip}." >&2
}

case "${1:-}" in
  select) select_release "${2:?image}" "${3:?sha}" ;;
  promote) promote "${2:?image}" "${3:?version}" "${4:?digest}" ;;
  reschedule) reschedule ;;
  publish) publish "${2:?image}" "${3:?version}" "${4-}" "${5:?sha}" ;;
  *) echo "usage: $0 select|promote|publish|reschedule ..." >&2; exit 2 ;;
esac
