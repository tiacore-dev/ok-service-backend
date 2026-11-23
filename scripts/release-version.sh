#!/bin/sh
# Production versioning from Conventional Commits. Annotated git tags vX.Y.Z are the source of truth.
#   release-version.sh next                   -> next version for HEAD (no "v"); empty output = nothing to release
#   release-version.sh notes <version>        -> Markdown release notes for <version>
#   release-version.sh check-latest <version> -> fails if a higher release tag already exists
set -eu

# Full history and tags are needed; CI checkouts may be shallow or lack tags.
REMOTE="${RELEASE_REMOTE:-origin}"
[ "$(git rev-parse --is-shallow-repository)" = true ] && git fetch --quiet --unshallow "$REMOTE"
git fetch --quiet --force --tags "$REMOTE"

semver_sort() { sed 's/^v//' | sort -t. -k1,1n -k2,2n -k3,3n; }
# Release tags: annotated only (the source of truth), SemVer without leading zeroes. Takes for-each-ref filters.
release_tags() {
  git for-each-ref --format='%(objecttype) %(refname:strip=2)' "$@" refs/tags \
    | awk '$1 == "tag" { print $2 }' \
    | grep -E '^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$' || true
}

# Highest vX.Y.Z tag reachable from HEAD (without "v"), optionally excluding one tag.
last_version() {
  release_tags --merged HEAD | grep -vxF "${1:-}" | semver_sort | tail -n1
}

# Prints breaking|feat|fix|perf|none for a commit.
classify() {
  subject="$(git log -1 --format=%s "$1")"
  if printf '%s\n' "$subject" | grep -qE '^[a-z]+(\([^)]*\))?!:' \
    || git log -1 --format=%b "$1" | grep -qE '^BREAKING[ -]CHANGE:'; then
    echo breaking
    return
  fi
  case "$subject" in
    feat:* | feat\(*\):*) echo feat ;;
    fix:* | fix\(*\):*) echo fix ;;
    perf:* | perf\(*\):*) echo perf ;;
    *) echo none ;;
  esac
}

next() {
  # Re-run of an already released commit keeps its version.
  head_version="$(release_tags --points-at HEAD | semver_sort | tail -n1)"
  [ -n "$head_version" ] && { echo "$head_version"; return; }

  # Never release a commit that is older than an existing release.
  highest="$(release_tags | semver_sort | tail -n1)"
  last="$(last_version)"
  if [ "$highest" != "$last" ]; then
    echo "HEAD does not contain the latest release v${highest}; refusing to release an older commit" >&2
    exit 1
  fi
  # First production release is 1.0.0 regardless of older commit messages.
  [ -z "$last" ] && { echo 1.0.0; return; }

  bump=none
  for sha in $(git log --no-merges --format=%H "v${last}..HEAD"); do
    case "$(classify "$sha")" in
      breaking) bump=major; break ;;
      feat) bump=minor ;;
      fix | perf) [ "$bump" = none ] && bump=patch ;;
    esac
  done

  major="${last%%.*}"; rest="${last#*.}"; minor="${rest%%.*}"; patch="${rest#*.}"
  case "$bump" in
    major) echo "$((major + 1)).0.0" ;;
    minor) echo "${major}.$((minor + 1)).0" ;;
    patch) echo "${major}.${minor}.$((patch + 1))" ;;
  esac
}

check_latest() {
  highest="$(release_tags | semver_sort | tail -n1)"
  [ -z "$highest" ] && return
  if [ "$(printf '%s\n%s\n' "$highest" "$1" | semver_sort | tail -n1)" != "$1" ]; then
    echo "A newer release v${highest} exists; refusing to deploy or publish ${1}" >&2
    exit 1
  fi
}

notes() {
  version="$1"
  prev="$(last_version "v${version}")"
  printf '## %s (%s)\n\n' "$version" "$(date -u +%Y-%m-%d)"
  if [ -z "$prev" ]; then
    echo "Initial production release."
    return
  fi

  # Commit text is untrusted: only ever expanded as data, never evaluated.
  nl='
'
  breaking=""; feat=""; fix=""; perf=""
  for sha in $(git log --no-merges --format=%H "v${prev}..HEAD"); do
    kind="$(classify "$sha")"
    line="- $(git log -1 --format=%s "$sha" | sed -E 's/^[a-z]+\(([^)]*)\)!?: */**\1:** /; s/^[a-z]+!?: *//') ($(git log -1 --format=%h "$sha"))${nl}"
    case "$kind" in
      breaking) breaking="${breaking}${line}" ;;
      feat) feat="${feat}${line}" ;;
      fix) fix="${fix}${line}" ;;
      perf) perf="${perf}${line}" ;;
    esac
  done

  [ -n "$breaking" ] && printf '### Breaking changes\n\n%s\n' "$breaking"
  [ -n "$feat" ] && printf '### Features\n\n%s\n' "$feat"
  [ -n "$fix" ] && printf '### Bug fixes\n\n%s\n' "$fix"
  [ -n "$perf" ] && printf '### Performance improvements\n\n%s\n' "$perf"
  printf 'Changes since %s.\n' "v${prev}"
}

case "${1:-}" in
  next) next ;;
  notes) notes "${2:?version required}" ;;
  check-latest) check_latest "${2:?version required}" ;;
  *) echo "usage: $0 next | notes <version> | check-latest <version>" >&2; exit 2 ;;
esac
