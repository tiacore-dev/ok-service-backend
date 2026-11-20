"""Production release automation: temporary Git history, fake registry, server and GitHub API."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from flask import Flask
from prometheus_client import CollectorRegistry, generate_latest

from app import setup_metrics

ROOT = Path(__file__).resolve().parents[1]
VERSION_SCRIPT = ROOT / "scripts/release-version.sh"
CI_SCRIPT = ROOT / "scripts/release-ci.sh"
DEPLOY_SCRIPT = ROOT / "scripts/deploy-production.sh"
IMAGE = "acme/ok-service-backend"
DIGEST = "sha256:" + "a" * 64

# CI sets RELEASE_TESTS_REQUIRED=1 so missing tools fail the run instead of skipping silently.
needs_git = pytest.mark.skipif(
    not (shutil.which("git") and shutil.which("jq"))
    and not os.getenv("RELEASE_TESTS_REQUIRED"),
    reason="needs git and jq",
)

FAKE_DOCKER_REGISTRY = r"""#!/usr/bin/env bash
printf '%s\n' "$*" >> "$REG/docker_calls"
[ "$1 $2" = "buildx imagetools" ] || exit 0
[ -f "$REG/ERROR" ] && { echo "ERROR: unauthorized: authentication required" >&2; exit 1; }
case "$3" in
  inspect)
    f="$REG/tags/${4##*:}"
    [ -f "$f" ] || { echo "ERROR: docker.io/$4: not found" >&2; exit 1; }
    read -r digest rev ver < "$f"
    if [ "${5:-}" = --format ]; then
      case "$6" in *revision*) echo "$rev" ;; *version*) echo "$ver" ;; esac
      exit 0
    fi
    printf 'Name: %s\nMediaType: application/vnd.oci.image.manifest.v1+json\nDigest: %s\n' "$4" "$digest" ;;
  create)
    while [ "$1" != -t ]; do shift; done
    echo "${3#*@} candidate candidate" > "$REG/tags/${2##*:}" ;;
esac
"""

FAKE_CURL = r"""#!/usr/bin/env bash
printf '%s\n' "$*" >> "$REG/curl_calls"
for arg in "$@"; do
  [ "$arg" = POST ] && { cat > "$REG/release_body.json"; exit "${POST_EXIT:-0}"; }
done
printf '%s' "${RELEASE_CODE:-404}"
"""

FAKE_GH = r"""#!/usr/bin/env bash
printf '%s\n' "$*" >> "$REG/gh_calls"
"""


def write_exe(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(0o755)


class Repo:
    """A work clone with a bare `origin`, fake docker/curl on PATH."""

    def __init__(self, tmp: Path):
        self.reg = tmp / "registry"
        (self.reg / "tags").mkdir(parents=True)
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        write_exe(bin_dir / "docker", FAKE_DOCKER_REGISTRY)
        write_exe(bin_dir / "curl", FAKE_CURL)
        write_exe(bin_dir / "gh", FAKE_GH)
        self.env = dict(
            os.environ,
            PATH=f"{bin_dir}:{os.environ['PATH']}",
            REG=str(self.reg),
            GIT_AUTHOR_NAME="t",
            GIT_AUTHOR_EMAIL="t@example.com",
            GIT_COMMITTER_NAME="t",
            GIT_COMMITTER_EMAIL="t@example.com",
            GIT_CONFIG_GLOBAL="/dev/null",
            GIT_CONFIG_NOSYSTEM="1",
            GITHUB_REPOSITORY="acme/ok-service-backend",
            GITHUB_TOKEN="test-token",
            GITHUB_RUN_ID="42",
            GITHUB_SERVER_URL="https://github.example",
        )
        self.work = tmp / "work"
        origin = tmp / "origin.git"
        subprocess.run(
            ["git", "init", "-q", "--bare", "-b", "master", str(origin)],
            env=self.env,
            check=True,
        )
        subprocess.run(
            ["git", "init", "-q", "-b", "master", str(self.work)],
            env=self.env,
            check=True,
        )
        self.git("remote", "add", "origin", str(origin))
        self.counter = 0

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=self.work,
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(
        self, subject: str, body: str = "", files: dict[str, str] | None = None
    ) -> str:
        self.counter += 1
        for name, text in (files or {f"file{self.counter}.txt": subject}).items():
            (self.work / name).parent.mkdir(parents=True, exist_ok=True)
            (self.work / name).write_text(text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", subject, *(["-m", body] if body else []))
        self.git("push", "-q", "-f", "origin", "HEAD:master")
        return self.git("rev-parse", "HEAD")

    def tag(self, version: str, ref: str = "HEAD") -> None:
        self.git("tag", "-a", f"v{version}", "-m", f"Release v{version}", ref)
        self.git("push", "-q", "origin", f"v{version}")

    def image(self, version: str, digest: str, revision: str) -> None:
        """Registry entries by tag and by digest (the fake keys refs by text after the last ':')."""
        entry = f"{digest} {revision} {version}\n"
        (self.reg / "tags" / version).write_text(entry)
        (self.reg / "tags" / digest.split(":")[1]).write_text(entry)

    def run(self, script: Path, *args: str, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(script), *args],
            cwd=self.work,
            env={**self.env, **env},
            capture_output=True,
            text=True,
            check=False,
        )

    def select(self, sha: str) -> dict[str, str]:
        result = self.run(CI_SCRIPT, "select", IMAGE, sha)
        assert result.returncode == 0, result.stderr
        return dict(line.split("=", 1) for line in result.stdout.splitlines())

    def next_version(self) -> str:
        result = self.run(VERSION_SCRIPT, "next")
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    def calls(self, name: str) -> str:
        path = self.reg / name
        return path.read_text() if path.exists() else ""


@pytest.fixture
def repo(tmp_path):
    return Repo(tmp_path)


def history_without_tags(repo: Repo) -> None:
    repo.commit("feat: OK-1 initial feature")
    repo.commit("fix: OK-2 old fix")
    repo.commit(
        "feat: OK-145 prices",
        files={"app/__init__.py": 'metrics.info("app_info", "x", version="1.0.3")\n'},
    )


# --- version selection -------------------------------------------------------------------------


@needs_git
def test_bootstrap_with_only_ci_commit_selects_1_0_0(repo):
    history_without_tags(repo)
    sha = repo.commit("ci: automate production releases")

    assert repo.next_version() == "1.0.0"
    assert repo.select(sha) == {"state": "new", "version": "1.0.0", "digest": ""}


@needs_git
@pytest.mark.parametrize(
    ("commits", "expected"),
    [
        ([("docs: readme", "")], ""),
        ([("ci: automate production releases", "")], ""),
        ([("fix: OK-3 bug", "")], "1.0.1"),
        ([("perf(db): faster", "")], "1.0.1"),
        ([("fix: a", ""), ("feat(works): OK-4 b", ""), ("fix: c", "")], "1.1.0"),
        ([("feat!: drop endpoint", "")], "2.0.0"),
        ([("fix(api)!: change shape", "")], "2.0.0"),
        ([("refactor: x", "BREAKING CHANGE: removes y")], "2.0.0"),
        ([("chore: x", "BREAKING-CHANGE: removes z")], "2.0.0"),
    ],
)
def test_subsequent_bump_uses_highest_change(repo, commits, expected):
    history_without_tags(repo)
    repo.tag("1.0.0")
    for subject, body in commits:
        repo.commit(subject, body)

    assert repo.next_version() == expected


@needs_git
def test_commits_introduced_by_merge_are_counted(repo):
    repo.commit("chore: base")
    repo.tag("1.0.0")
    repo.git("checkout", "-q", "-b", "feature")
    repo.commit("feat: OK-5 on branch")
    repo.git("checkout", "-q", "master")
    repo.commit("docs: on master")
    repo.git("merge", "-q", "--no-ff", "-m", "Merge branch 'feature'", "feature")
    repo.git("push", "-q", "origin", "HEAD:master")

    assert repo.next_version() == "1.1.0"


@needs_git
def test_no_release_worthy_commits_is_none(repo):
    sha = repo.commit("feat: base")
    repo.tag("1.0.0")
    sha = repo.commit("docs: notes")

    assert repo.select(sha) == {"state": "none"}


@needs_git
def test_superseded_run_is_outdated(repo):
    old = repo.commit("feat: a")
    repo.commit("fix: b")
    repo.git("checkout", "-q", "--detach", old)

    assert repo.select(old) == {"state": "outdated"}


@needs_git
def test_full_rerun_finishes_promoted_release_after_master_advances(repo):
    """A promoted 1.0.0, its run failed before tagging; B (fix) reached master; A is rerun in full."""
    a = repo.commit("feat: OK-1 a")
    repo.image("1.0.0", DIGEST, a)  # durable evidence of A's promotion
    b = repo.commit("fix: OK-2 b")

    # B must not take over A's version while A's release is unfinished.
    conflict = repo.run(CI_SCRIPT, "select", IMAGE, b)
    assert conflict.returncode != 0
    assert f"revision={a}" in conflict.stderr

    # Full rerun of A: initial selection, no outputs from the failed attempt.
    repo.git("checkout", "-q", "--detach", a)
    assert repo.select(a) == {"state": "resume", "version": "1.0.0", "digest": DIGEST}
    # Deploy-time recheck is the same call and agrees.
    assert repo.select(a) == {"state": "resume", "version": "1.0.0", "digest": DIGEST}

    published = repo.run(CI_SCRIPT, "publish", IMAGE, "1.0.0", DIGEST, a)
    assert published.returncode == 0, published.stderr
    assert remote_tag_target(repo, "v1.0.0") == a

    # A rerun after publication only finishes publication (idempotent), no redeploy.
    assert repo.select(a)["state"] == "released"

    # B now releases on top of A.
    repo.git("checkout", "-q", "--detach", b)
    assert repo.select(b) == {"state": "new", "version": "1.0.1", "digest": ""}

    # Once B is released, a stale rerun of A is a no-op, never a rollback.
    repo.image("1.0.1", "sha256:" + "b" * 64, b)
    repo.tag("1.0.1", b)
    repo.git("checkout", "-q", "--detach", a)
    assert repo.select(a) == {"state": "outdated"}


@needs_git
def test_superseded_run_with_another_commits_image_is_a_noop(repo):
    old = repo.commit("feat: a")
    repo.image("1.0.0", DIGEST, "f" * 40)
    repo.commit("fix: b")
    repo.git("checkout", "-q", "--detach", old)

    assert repo.select(old) == {"state": "outdated"}


@needs_git
def test_promoted_release_is_not_resumed_when_master_was_rewritten(repo):
    base = repo.commit("chore: base")
    old = repo.commit("feat: a")
    repo.image("1.0.0", DIGEST, old)
    repo.git("checkout", "-q", "-b", "rewritten", base)
    repo.commit("fix: replacement")  # force-pushed over master
    repo.git("checkout", "-q", "--detach", old)

    assert repo.select(old) == {"state": "outdated"}


@needs_git
def test_older_revision_than_latest_release_is_refused(repo):
    old = repo.commit("feat: a")
    repo.commit("fix: b")
    repo.tag("1.0.0")
    repo.git("reset", "-q", "--hard", old)
    repo.git("push", "-q", "-f", "origin", "HEAD:master")

    result = repo.run(CI_SCRIPT, "select", IMAGE, old)
    assert result.returncode != 0
    assert "refusing to release an older commit" in result.stderr


@needs_git
def test_retry_of_existing_release_keeps_its_version(repo):
    repo.commit("feat: base")
    repo.tag("1.0.0")
    sha = repo.commit("feat: OK-6 new")
    repo.tag("1.1.0")
    repo.image("1.1.0", DIGEST, sha)

    assert repo.select(sha) == {
        "state": "released",
        "version": "1.1.0",
        "digest": DIGEST,
    }


@needs_git
def test_existing_image_of_this_commit_is_resumed(repo):
    sha = repo.commit("feat: base")
    repo.image("1.0.0", DIGEST, sha)

    assert repo.select(sha) == {"state": "resume", "version": "1.0.0", "digest": DIGEST}


@needs_git
def test_version_image_from_another_commit_is_a_conflict(repo):
    sha = repo.commit("feat: base")
    repo.image("1.0.0", DIGEST, "f" * 40)

    result = repo.run(CI_SCRIPT, "select", IMAGE, sha)
    assert result.returncode != 0
    assert "revision=" + "f" * 40 in result.stderr


@needs_git
def test_registry_error_is_not_treated_as_missing_image(repo):
    sha = repo.commit("feat: base")
    (repo.reg / "ERROR").touch()

    result = repo.run(CI_SCRIPT, "select", IMAGE, sha)
    assert result.returncode != 0
    assert "Cannot check registry" in result.stderr


@needs_git
def test_promoted_release_resumes_with_other_remote_branches(repo):
    """FETCH_HEAD after the tag fetch may name another branch; ancestry must use master."""
    base = repo.commit("chore: base")
    repo.git("push", "-q", "origin", f"{base}:refs/heads/aaa")  # sorts before master
    a = repo.commit("feat: a")
    repo.image("1.0.0", DIGEST, a)
    repo.commit("fix: b")
    repo.git("checkout", "-q", "--detach", a)

    assert repo.select(a) == {"state": "resume", "version": "1.0.0", "digest": DIGEST}


@needs_git
def test_labels_are_read_from_the_resolved_digest(repo):
    """The tag resolved to D1, then moved to an image with the expected labels: D1 must not pass."""
    sha = repo.commit("feat: base")
    repo.tag("1.0.0")
    repo.image("1.0.0", DIGEST, sha)  # labels as read through the (moved) tag
    (repo.reg / "tags" / DIGEST.split(":")[1]).write_text(
        f"{DIGEST} {'f' * 40} 1.0.0\n"
    )

    result = repo.run(CI_SCRIPT, "select", IMAGE, sha)

    assert result.returncode != 0
    assert "revision=" + "f" * 40 in result.stderr


@needs_git
def test_lightweight_tag_is_not_a_release_baseline(repo):
    repo.commit("feat: a")
    repo.git("tag", "v1.0.0")
    repo.git("push", "-q", "origin", "v1.0.0")
    repo.commit("fix: b")

    assert repo.next_version() == "1.0.0"


@needs_git
@pytest.mark.parametrize(("tag", "expected"), [("1.0.08", "1.0.0"), ("1.0.8", "1.0.9")])
def test_tags_with_leading_zeroes_are_not_releases(repo, tag, expected):
    repo.commit("feat: a")
    repo.tag(tag)
    repo.commit("fix: b")

    assert repo.next_version() == expected


@needs_git
def test_reschedule_queues_unreleased_master_tip(repo):
    repo.commit("feat: a")

    result = repo.run(CI_SCRIPT, "reschedule")

    assert result.returncode == 0, result.stderr
    assert repo.calls("gh_calls") == "workflow run deploy.yml --ref master\n"


@needs_git
def test_reschedule_skips_released_master_tip(repo):
    repo.commit("feat: a")
    repo.tag("1.0.0")

    result = repo.run(CI_SCRIPT, "reschedule")

    assert result.returncode == 0, result.stderr
    assert repo.calls("gh_calls") == ""


# --- promotion ---------------------------------------------------------------------------------


@needs_git
def test_promote_tags_candidate_digest(repo):
    result = repo.run(CI_SCRIPT, "promote", IMAGE, "1.0.0", DIGEST)
    assert result.returncode == 0, result.stderr
    assert (
        f"imagetools create --prefer-index=false -t {IMAGE}:1.0.0 {IMAGE}@{DIGEST}"
        in repo.calls("docker_calls")
    )


@needs_git
def test_promote_is_idempotent_for_same_digest(repo):
    repo.image("1.0.0", DIGEST, "x")
    result = repo.run(CI_SCRIPT, "promote", IMAGE, "1.0.0", DIGEST)
    assert result.returncode == 0, result.stderr
    assert "create" not in repo.calls("docker_calls")


@needs_git
def test_promote_never_overwrites_another_digest(repo):
    repo.image("1.0.0", "sha256:" + "b" * 64, "x")
    result = repo.run(CI_SCRIPT, "promote", IMAGE, "1.0.0", DIGEST)
    assert result.returncode != 0
    assert "create" not in repo.calls("docker_calls")


# --- publication -------------------------------------------------------------------------------


def remote_tag_target(repo: Repo, tag: str) -> str:
    """Commit of the annotated tag as origin advertises it (a local-only tag does not count)."""
    advertised = repo.git("ls-remote", "origin", f"refs/tags/{tag}").split()
    assert advertised[1:] == [f"refs/tags/{tag}"], advertised
    repo.git(
        "fetch", "-q", "origin", f"refs/tags/{tag}"
    )  # the advertised object, not a local tag
    assert repo.git("cat-file", "-t", advertised[0]) == "tag"
    return repo.git("rev-parse", f"{advertised[0]}^{{commit}}")


@needs_git
def test_bootstrap_publication_creates_annotated_tag_and_release(repo):
    history_without_tags(repo)
    sha = repo.commit("ci: automate production releases")

    result = repo.run(CI_SCRIPT, "publish", IMAGE, "1.0.0", DIGEST, sha)

    assert result.returncode == 0, result.stderr
    assert remote_tag_target(repo, "v1.0.0") == sha
    body = json.loads(repo.calls("release_body.json"))
    assert body["tag_name"] == body["name"] == "v1.0.0"
    for text in (
        "## 1.0.0 (",
        "Initial production release.",
        sha,
        DIGEST,
        "/actions/runs/42",
    ):
        assert text in body["body"]


@needs_git
def test_subsequent_notes_group_changes(repo):
    repo.commit("feat: base")
    repo.tag("1.0.0")
    repo.commit("feat(works): OK-7 tree")
    repo.commit("fix: OK-8 bug")
    sha = repo.commit("docs: notes")

    result = repo.run(CI_SCRIPT, "publish", IMAGE, "1.1.0", DIGEST, sha)

    assert result.returncode == 0, result.stderr
    notes = json.loads(repo.calls("release_body.json"))["body"]
    assert "### Features\n\n- **works:** OK-7 tree" in notes
    assert "### Bug fixes\n\n- OK-8 bug" in notes
    assert "docs" not in notes.split("---")[0].replace("Changes since", "")
    assert "Changes since v1.0.0." in notes


@needs_git
def test_publication_retry_with_tag_but_no_release_finishes_release(repo):
    sha = repo.commit("feat: base")
    repo.tag("1.0.0")
    tag_object = repo.git("rev-parse", "refs/tags/v1.0.0")

    result = repo.run(
        CI_SCRIPT, "publish", IMAGE, "1.0.0", DIGEST, sha, RELEASE_CODE="404"
    )

    assert result.returncode == 0, result.stderr
    assert repo.git("ls-remote", "origin", "refs/tags/v1.0.0").split()[0] == tag_object
    assert "POST" in repo.calls("curl_calls")


@needs_git
def test_publication_retry_with_tag_and_release_succeeds_without_changes(repo):
    sha = repo.commit("feat: base")
    repo.tag("1.0.0")

    result = repo.run(
        CI_SCRIPT, "publish", IMAGE, "1.0.0", DIGEST, sha, RELEASE_CODE="200"
    )

    assert result.returncode == 0, result.stderr
    assert "POST" not in repo.calls("curl_calls")


@needs_git
def test_existing_tag_on_another_commit_is_never_moved(repo):
    repo.commit("feat: base")
    repo.tag("1.0.0")
    sha = repo.commit("fix: later")

    result = repo.run(CI_SCRIPT, "publish", IMAGE, "1.0.0", DIGEST, sha)

    assert result.returncode != 0
    assert "never moved" in result.stderr
    assert repo.calls("curl_calls") == ""


@needs_git
def test_publication_retry_refuses_commit_dropped_from_master(repo):
    base = repo.commit("chore: base")
    a = repo.commit("feat: a")
    repo.git("checkout", "-q", "-b", "rewritten", base)
    repo.commit("fix: replacement")  # force-pushed over master after A deployed
    repo.git("checkout", "-q", "--detach", a)

    result = repo.run(CI_SCRIPT, "publish", IMAGE, "1.0.0", DIGEST, a)

    assert result.returncode != 0
    assert "no longer on master; not creating v1.0.0" in result.stderr
    assert repo.git("ls-remote", "origin", "refs/tags/v1.0.0") == ""
    assert "POST" not in repo.calls("curl_calls")


@needs_git
def test_lightweight_tag_is_rejected(repo):
    sha = repo.commit("feat: base")
    repo.git("tag", "v1.0.0")
    repo.git("push", "-q", "origin", "v1.0.0")

    result = repo.run(CI_SCRIPT, "publish", IMAGE, "1.0.0", DIGEST, sha)

    assert result.returncode != 0
    assert "not an annotated tag" in result.stderr


@needs_git
def test_release_api_auth_failure_is_not_treated_as_missing(repo):
    sha = repo.commit("feat: base")

    result = repo.run(
        CI_SCRIPT, "publish", IMAGE, "1.0.0", DIGEST, sha, RELEASE_CODE="401"
    )

    assert result.returncode != 0
    assert "HTTP 401" in result.stderr
    assert "POST" not in repo.calls("curl_calls")


@needs_git
def test_publication_refuses_version_older_than_latest_release(repo):
    repo.commit("feat: base")
    repo.tag("1.1.0")
    sha = repo.commit("fix: later")

    result = repo.run(CI_SCRIPT, "publish", IMAGE, "1.0.1", DIGEST, sha)

    assert result.returncode != 0
    assert "newer release v1.1.0" in result.stderr


# --- server deployment -------------------------------------------------------------------------

SHA = "c" * 40

FAKE_DOCKER_SERVER = r"""#!/usr/bin/env bash
# Emulates Compose image resolution: the pin file wins when passed (unless PIN_IGNORED),
# otherwise web is ${DOCKERHUB_USERNAME}/ok-service-backend:${TAG} from .env.
web_image() {
  if [[ " $* " == *" -f .release-compose.yaml "* && -z "${PIN_IGNORED:-}" ]]; then
    sed -n 's/^    image: //p' .release-compose.yaml
  else
    echo "$(sed -n 's/^DOCKERHUB_USERNAME=//p' .env)/ok-service-backend:$(sed -n 's/^TAG=//p' .env)"
  fi
}
line="$*"
case "$*" in compose*" run "* | compose*" up "* | compose*" exec "*) line="$line [image=$(web_image "$@")]" ;; esac
printf '%s\n' "$line" >> "$CALLS"
case "$*" in
  # web depends on redis (another image); its environment carries a secret that must never be logged.
  "compose "*" config --format json")
    printf '{"services": {"redis": {"image": "redis:7"}, "web": {"image": "%s", "depends_on": {"redis": {}}, "environment": {"DB_PASSWORD": "s3cret"}}}}\n' "$(web_image "$@")" ;;
  # The parser container: run its python code with the host python.
  "run --rm -i --network none --entrypoint python "*) shift $(( $# - 1 )); exec python3 -c "$1" ;;
  "compose "*" ps -q web") echo container-id ;;
  "compose "*" exec -T web "*) exit "${READY_EXIT:-0}" ;;
  "compose "*rebuild-project-material-statistics) exit "${REBUILD_EXIT:-0}" ;;
  "image inspect --format {{.Id}} "*@*) echo sha256:release ;;
  "image inspect --format {{.Id}} "*) echo "${TAG_ID:-sha256:release}" ;;
  "inspect --format {{.Image}} "*) echo "${RUNNING_ID:-sha256:release}" ;;
esac
exit 0
"""

FAKE_GIT_SERVER = r"""#!/usr/bin/env bash
printf 'git %s\n' "$*" >> "$CALLS"
case "$*" in
  "rev-parse HEAD") echo "$HEAD_SHA" ;;
  "diff --quiet") exit "${UNSTAGED:-0}" ;;
  "diff --cached --quiet") exit "${STAGED:-0}" ;;
esac
exit 0
"""

ENV_FILE = "DOCKERHUB_USERNAME=wrong-user\nTAG=old-sha\nOTHER=1\n"
REF = f"{IMAGE}@{DIGEST}"


def deploy(
    tmp_path: Path,
    marker: str | None = None,
    version: str = "1.0.0",
    env_text: str | None = ENV_FILE,
    **env: str,
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    write_exe(bin_dir / "docker", FAKE_DOCKER_SERVER)
    write_exe(bin_dir / "git", FAKE_GIT_SERVER)
    write_exe(bin_dir / "sleep", "#!/usr/bin/env bash\nexit 0\n")
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    if env_text is not None:  # None keeps the project from a previous attempt
        (project / ".env").write_text(env_text)
    if marker is not None:
        (project / ".release-state").write_text(marker)
    calls = tmp_path / "calls"
    calls.write_text("")
    # Fed through stdin exactly like the workflow: ssh host 'bash -s -- ...' < script.
    with DEPLOY_SCRIPT.open() as script:
        result = subprocess.run(
            ["bash", "-s", "--", SHA, IMAGE, version, DIGEST, "77"],
            stdin=script,
            cwd=project,
            env=dict(
                os.environ,
                PATH=f"{bin_dir}:{os.environ['PATH']}",
                CALLS=str(calls),
                HEAD_SHA=env.pop("HEAD_SHA", SHA),
                **env,
            ),
            capture_output=True,
            text=True,
            check=False,
        )
    state = project / ".release-state"
    return (
        result,
        calls.read_text().splitlines(),
        (project / ".env").read_text(),
        state.read_text() if state.exists() else None,
    )


def marker_for(version: str = "1.0.0", sha: str = SHA, digest: str = DIGEST) -> str:
    return f"VERSION={version}\nSHA={sha}\nDIGEST={digest}\nRUN_ID=1\n"


def index_of(calls: list[str], text: str) -> int:
    return next(i for i, call in enumerate(calls) if text in call)


def touched(calls: list[str], text: str) -> bool:
    return any(text in call for call in calls)


def test_deploy_runs_sequence_and_records_completion_last(tmp_path):
    result, calls, env_file, state = deploy(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "DEPLOY_RESULT=deployed" in result.stdout
    assert f"Compose web.image: {REF}" in result.stdout
    assert "s3cret" not in result.stdout + result.stderr
    assert index_of(calls, "git diff --quiet") < index_of(calls, "git merge")
    assert "git merge -q --ff-only " + SHA in calls
    order = [
        index_of(calls, "config --format json"),
        index_of(calls, "alembic upgrade head"),
        index_of(calls, "up -d --force-recreate web"),
        index_of(calls, "exec -T web python"),
        index_of(calls, "rebuild-project-work-statistics"),
        index_of(calls, "rebuild-project-material-statistics"),
    ]
    assert order == sorted(order)
    for i in order:
        assert (
            "-f docker-compose.app.yaml -f docker-compose.prod.yaml -f .release-compose.yaml"
            in calls[i]
        )
    # Despite DOCKERHUB_USERNAME=wrong-user in .env, migrations, restart, probe and rebuilds use the digest.
    for i in order[1:]:
        assert calls[i].endswith(f"[image={REF}]"), calls[i]
    assert not touched(calls, "push-worker") and not touched(calls, "template-service")
    assert env_file == "DOCKERHUB_USERNAME=wrong-user\nTAG=1.0.0\nOTHER=1\n"
    assert state is not None
    assert state.startswith(
        f"VERSION=1.0.0\nSHA={SHA}\nDIGEST={DIGEST}\nRUN_ID=77\nDEPLOYED_AT="
    )


def test_unpinned_web_image_stops_before_env_and_alembic(tmp_path):
    # Compose ignores the pin -> web would come from wrong-user's repository.
    result, calls, env_file, state = deploy(tmp_path, PIN_IGNORED="1")

    assert result.returncode != 0
    assert (
        "Compose resolves web to 'wrong-user/ok-service-backend:old-sha'"
        in result.stderr
    )
    assert not touched(calls, "alembic")
    assert not touched(calls, " run ") and not touched(calls, " up ")
    assert env_file == ENV_FILE
    assert state is None


@pytest.mark.parametrize("dirty", [{"UNSTAGED": "1"}, {"STAGED": "1"}])
def test_tracked_changes_block_checkout_update(tmp_path, dirty):
    result, calls, env_file, state = deploy(tmp_path, **dirty)

    assert result.returncode != 0
    assert "changes to tracked files" in result.stderr
    assert not touched(calls, "git fetch") and not touched(calls, "git merge")
    assert not touched(calls, "compose")
    assert env_file == ENV_FILE
    assert state is None


def test_completed_deployment_is_recognized_without_migrations_or_rebuilds(tmp_path):
    result, calls, env_file, _ = deploy(tmp_path, marker=marker_for())

    assert result.returncode == 0, result.stderr
    assert "DEPLOY_RESULT=already-deployed" in result.stdout
    assert touched(calls, "exec -T web python -c import sys, urllib.request")
    assert not any(
        "alembic" in c or "rebuild" in c or c.startswith("git ") for c in calls
    )
    assert env_file == ENV_FILE


def test_completed_deployment_with_unready_web_fails_without_changes(tmp_path):
    result, calls, env_file, state = deploy(
        tmp_path, marker=marker_for(), READY_EXIT="1"
    )

    assert result.returncode != 0
    assert "deployed but web is not ready" in result.stderr
    assert "DEPLOY_RESULT" not in result.stdout
    assert sum("exec -T web python" in c for c in calls) == 30  # bounded probe
    assert not any(
        "alembic" in c or "rebuild" in c or c.startswith("git ") for c in calls
    )
    assert env_file == ENV_FILE
    assert state == marker_for()


@pytest.mark.parametrize(
    ("marker", "message"),
    [
        (marker_for("1.2.0"), "newer release 1.2.0"),
        (marker_for(sha="d" * 40), "another commit"),
    ],
)
def test_deploy_refuses_newer_or_conflicting_release(tmp_path, marker, message):
    result, calls, _, state = deploy(tmp_path, marker=marker, version="1.0.0")

    assert result.returncode != 0
    assert message in result.stderr
    assert not any("alembic" in c or c.startswith("git ") for c in calls)
    assert state == marker


def test_deploy_upgrades_over_older_release(tmp_path):
    result, _, _, state = deploy(
        tmp_path, marker=marker_for("1.0.0", sha="d" * 40), version="1.1.0"
    )

    assert result.returncode == 0, result.stderr
    assert state is not None
    assert state.startswith(f"VERSION=1.1.0\nSHA={SHA}\n")


@pytest.mark.parametrize(
    ("env", "message", "stops_before"),
    [
        ({"HEAD_SHA": "e" * 40}, "checkout is not", "compose"),
        ({"TAG_ID": "sha256:other"}, "does not match the verified digest", "compose"),
        ({"RUNNING_ID": "sha256:other"}, "is not running", "rebuild"),
        ({"READY_EXIT": "1"}, "did not become ready", "rebuild"),
        ({"REBUILD_EXIT": "1"}, "", None),
    ],
)
def test_failed_step_does_not_record_completion(tmp_path, env, message, stops_before):
    result, calls, env_file, state = deploy(tmp_path, **env)

    assert result.returncode != 0
    assert message in result.stderr
    assert state is None
    if stops_before:
        assert not touched(calls, stops_before)
    if stops_before == "compose":
        assert env_file == ENV_FILE


def test_tag_is_appended_without_merging_an_unterminated_last_entry(tmp_path):
    result, _, env_file, _ = deploy(tmp_path, env_text="DB_PASSWORD=secret")

    assert result.returncode == 0, result.stderr
    assert env_file == "DB_PASSWORD=secret\nTAG=1.0.0\n"


def test_retry_after_failed_material_rebuild_completes_deployment(tmp_path):
    first, _, _, state = deploy(tmp_path, REBUILD_EXIT="1")
    assert first.returncode != 0 and state is None

    # Same project, .env and "running" image; only the rebuild failure is gone.
    second, calls, env_file, state = deploy(tmp_path, env_text=None)

    assert second.returncode == 0, second.stderr
    assert "DEPLOY_RESULT=deployed" in second.stdout
    assert touched(calls, "rebuild-project-material-statistics")
    assert env_file == "DOCKERHUB_USERNAME=wrong-user\nTAG=1.0.0\nOTHER=1\n"
    assert state is not None and state.startswith("VERSION=1.0.0\n")


# --- app_info ----------------------------------------------------------------------------------


@pytest.mark.parametrize(("value", "expected"), [("1.0.0", "1.0.0"), (None, "dev")])
def test_app_info_reports_release_version(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("APP_VERSION", raising=False)
    else:
        monkeypatch.setenv("APP_VERSION", value)
    registry = CollectorRegistry()

    setup_metrics(Flask(__name__), registry=registry)

    # deploy-production.sh waits for exactly this sample on /metrics.
    assert f'app_info{{version="{expected}"}} 1.0' in generate_latest(registry).decode()
