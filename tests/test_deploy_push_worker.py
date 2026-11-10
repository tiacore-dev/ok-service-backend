"""Deployment orchestration tests; no Docker daemon or Firebase is used."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/deploy-push-worker.sh"


class DeployPushWorkerTest(unittest.TestCase):
    def run_deploy(self, **settings):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docker = root / "docker"
            docker.write_text('''#!/usr/bin/env bash
printf '%q ' "$@" >> "$CALLS"
printf '\\n' >> "$CALLS"
case "$*" in
  "ps -q "*) [[ "${MANUAL:-0}" == 1 ]] && echo manual; exit 0 ;;
  *" run "*) exit "${PREFLIGHT_EXIT:-0}" ;;
  *" ps -q push-worker") echo worker-id ;;
  "inspect "*) echo "${STATE:-running 0}" ;;
esac
''')
            docker.chmod(0o755)
            sleep = root / "sleep"
            sleep.write_text("#!/usr/bin/env bash\nexit 0\n")
            sleep.chmod(0o755)
            calls = root / "calls"
            env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", CALLS=str(calls), **settings)
            result = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=False)
            return result, calls.read_text().splitlines()

    def test_success_and_repeated_deployment_recreate_one_service(self):
        for _ in range(2):
            result, calls = self.run_deploy()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(" run --rm --no-deps ", calls[1])
            self.assertIn(" up -d --no-deps --force-recreate --scale push-worker=1 push-worker", calls[2])
            self.assertTrue(calls[-1].startswith("inspect "))

    def test_manual_worker_blocks_start(self):
        result, calls = self.run_deploy(MANUAL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)

    def test_preflight_failure_blocks_start(self):
        result, calls = self.run_deploy(PREFLIGHT_EXIT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 2)

    def test_restart_loop_fails_deployment(self):
        result, _ = self.run_deploy(STATE="restarting 2")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
