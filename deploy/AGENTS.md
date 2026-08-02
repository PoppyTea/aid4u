# Deploy Module

## Purpose
VPS deployment tooling: sync + restart via `deploy.sh`, systemd unit definitions for
long-running task servers, and public-tunnel scripts (ngrok) for tasks that expose an
HTTP endpoint to an external bot (e.g. s01e03 proxy).

## Ownership
- `deploy.sh`: one-command deploy — `git pull` + `uv sync` + optional `systemctl restart` on the VPS.
- `systemd/`: unit files, one per long-running task server. `ExecStart` points at
  `tasks.<sXXeYY>.server` — keep the unit in sync with the task module path.
- `ngrok_tunnel.sh`: launches a public tunnel for a local task server port, for tasks
  whose grading bot needs to reach a publicly addressable URL.

## Local Contracts
- Every task server exposed via systemd MUST have a matching unit file here, named
  `aid4u-<task-slug>.service`.
- Secrets (VPS host/user, tunnel tokens) come from `.env` — never hardcode them here.

## Work Guidance
- `ngrok` itself is an external prerequisite (not a Python dependency) — install and
  `ngrok config add-authtoken` on whichever machine runs the tunnel before use.
- Prefer one systemd unit per task server; don't multiplex unrelated servers behind one unit.

## Verification
- `./deploy/deploy.sh [service-name]` against the VPS; `systemctl status` output confirms the restart.

## Child DOX Index
- None.
