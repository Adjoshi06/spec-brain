"""Run the deterministic check inside a locked-down Docker container.

The container has no network, a read-only root filesystem, every capability dropped, and
runs as an unprivileged user. If Docker is unavailable the check still runs locally, but the
result is labelled UNSANDBOXED so the failure is never silent.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "spec_check.py"
CONTAINER = os.environ.get("SANDBOX_CONTAINER", "specbrain-sandbox")
IMAGE = "python:3.12-slim"
RUN_ARGS = [
    "--network", "none",
    "--read-only",
    "--tmpfs", "/tmp:rw,size=64m",
    "--cap-drop", "ALL",
    "--security-opt", "no-new-privileges",
    "--pids-limit", "128",
    "--memory", "512m",
    "--user", "65534:65534",
]


def _docker(*args, timeout=60):
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def container_state():
    proc = _docker("inspect", "-f", "{{.State.Status}}", CONTAINER, timeout=20)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def ensure_container():
    """Start the sandbox container if it is not already running."""
    state = container_state()
    if state == "running":
        return CONTAINER
    if state is not None:
        _docker("rm", "-f", CONTAINER, timeout=30)
    proc = _docker(
        "run", "-d", "--name", CONTAINER, *RUN_ARGS,
        "--mount", f"type=bind,source={SCRIPT},target=/work/spec_check.py,readonly",
        "-w", "/work", IMAGE, "sleep", "infinity",
        timeout=90,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"docker run failed: {proc.stderr.strip()}")
    return CONTAINER


def _run_local(payload):
    proc = subprocess.run([sys.executable, str(SCRIPT), payload], capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return json.loads(proc.stdout)


def run_check(requirements, candidate):
    """Return {"result": <spec_check output>, "sandbox": <how it ran>}."""
    payload = json.dumps({"requirements": requirements, "candidate": candidate})
    started = time.perf_counter()
    try:
        ensure_container()
        proc = _docker("exec", CONTAINER, "python", "/work/spec_check.py", payload, timeout=60)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"exit code {proc.returncode}")
        result = json.loads(proc.stdout)
        sandbox = {
            "mode": "docker",
            "container": CONTAINER,
            "image": IMAGE,
            "network": "none",
            "read_only_rootfs": True,
            "capabilities": "all dropped",
            "user": "nobody (65534)",
            "seconds": round(time.perf_counter() - started, 2),
        }
    except Exception as exc:  # noqa: BLE001 - any sandbox failure falls back loudly
        result = _run_local(payload)
        sandbox = {
            "mode": "UNSANDBOXED",
            "reason": str(exc)[:300],
            "seconds": round(time.perf_counter() - started, 2),
        }
    return {"result": result, "sandbox": sandbox}


def prove_isolation():
    """Show that the container cannot reach the network (for the demo audit trail)."""
    ensure_container()
    proc = _docker(
        "exec", CONTAINER, "python", "-c",
        "import urllib.request; urllib.request.urlopen('https://example.com', timeout=3)",
        timeout=30,
    )
    if proc.returncode == 0:
        return "UNEXPECTED: the sandbox reached the network"
    last_line = (proc.stderr.strip().splitlines() or ["blocked"])[-1]
    return f"network call blocked inside sandbox: {last_line}"


def policy_summary():
    proc = _docker(
        "inspect", "-f",
        "network={{.HostConfig.NetworkMode}} readonly={{.HostConfig.ReadonlyRootfs}} "
        "capdrop={{.HostConfig.CapDrop}} pids={{.HostConfig.PidsLimit}} user={{.Config.User}}",
        CONTAINER, timeout=20,
    )
    return proc.stdout.strip() if proc.returncode == 0 else f"not running: {proc.stderr.strip()}"


if __name__ == "__main__":
    demo = run_check(
        {"nrc_min": 0.85, "fire_classes": ["Class A"], "size": "24x24", "recycled_min": 0.30},
        {"nrc": 0.95, "fire_class": "Class A", "size": "24x24", "recycled": None},
    )
    print(json.dumps(demo, indent=2))
    print(policy_summary())
    print(prove_isolation())
